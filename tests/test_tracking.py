from decimal import Decimal

import pytest

from database.models import CargoCategory, ShipmentStatus as S, TransportType
from services.shipment_service import ShipmentCreate, create_shipment
from services.tracking_service import (
    InvalidTransitionError, StaleStatusError, allowed_next_statuses, change_status, flow_for, get_history,
)
from utils.formatting import shipment_card, timeline


async def _shipment(session, user, origin="shymkent", destination="tashkent"):
    payload = ShipmentCreate(origin=origin, destination=destination, cargo_category=CargoCategory.FOOD,
                             weight=Decimal("200"), volume=Decimal("1"), packages=5,
                             transport_type=TransportType.ROAD)
    shipment, _ = await create_shipment(session, user, payload)
    return shipment


# 7–8. Изменение статуса и история
async def test_full_status_chain_with_history(session, user):
    shipment = await _shipment(session, user)
    chain = [S.CONFIRMED, S.PREPARING, S.PICKED_UP, S.IN_TRANSIT, S.AT_CUSTOMS, S.CUSTOMS_CLEARED,
             S.ARRIVED, S.DELIVERED]
    for status in chain:
        change = await change_status(session, shipment.id, status, comment="test", changed_by=777)
        assert change.new_status == status
    history = await get_history(session, shipment.id)
    assert [h.new_status for h in history] == [S.CREATED, S.PENDING, *chain]
    assert history[-1].old_status == S.ARRIVED and history[-1].changed_by == 777
    assert change.shipment.status == S.DELIVERED
    assert allowed_next_statuses(change.shipment) == []


async def test_invalid_transition_rejected(session, user):
    shipment = await _shipment(session, user)
    with pytest.raises(InvalidTransitionError):
        await change_status(session, shipment.id, S.DELIVERED)
    assert len(await get_history(session, shipment.id)) == 2  # история не изменилась


async def test_stale_button_does_not_apply_twice(session, user):
    shipment = await _shipment(session, user)
    await change_status(session, shipment.id, S.CONFIRMED, expected_old=S.PENDING)
    with pytest.raises(StaleStatusError):  # повторное нажатие той же кнопки
        await change_status(session, shipment.id, S.CONFIRMED, expected_old=S.PENDING)
    assert [h.new_status for h in await get_history(session, shipment.id)].count(S.CONFIRMED) == 1


async def test_domestic_route_has_no_customs(session, user):
    shipment = await _shipment(session, user, "shymkent", "almaty")
    assert S.AT_CUSTOMS not in flow_for(shipment)
    for status in (S.CONFIRMED, S.PREPARING, S.PICKED_UP, S.IN_TRANSIT):
        await change_status(session, shipment.id, status)
    await session.refresh(shipment)
    assert allowed_next_statuses(shipment) == [S.ARRIVED, S.CANCELLED]
    with pytest.raises(InvalidTransitionError):
        await change_status(session, shipment.id, S.AT_CUSTOMS)


async def test_cancel_and_final_state(session, user):
    shipment = await _shipment(session, user)
    await change_status(session, shipment.id, S.CANCELLED)
    with pytest.raises(InvalidTransitionError):
        await change_status(session, shipment.id, S.CONFIRMED)


async def test_timeline_rendering(session, user):
    shipment = await _shipment(session, user)
    await change_status(session, shipment.id, S.CONFIRMED)
    await session.refresh(shipment)
    text = timeline(shipment, "ru")
    assert "✅ Заявка создана" in text and "🟠 <b>Подтверждена</b>" in text and "⚪️ Доставлен" in text
    card = shipment_card(shipment, "en")
    for part in (shipment.tracking_number, "Shymkent", "Tashkent", "200 kg", "Confirmed"):
        assert part in card
