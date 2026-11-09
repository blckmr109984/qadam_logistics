from datetime import date, timedelta
from decimal import Decimal

import pytest
from pydantic import ValidationError
from sqlalchemy import select

from database.models import CargoCategory, Shipment, ShipmentHistory, ShipmentStatus, TransportType, User
from services import shipment_service
from services.shipment_service import AccessDeniedError, ShipmentCreate, create_shipment, get_shipment_for_user
from services.user_service import get_or_create_user
from utils.tracking_id import generate_tracking_number, is_valid_tracking_number, normalize_tracking_number
from utils.validators import InputError, normalize_phone, parse_date, parse_packages, parse_volume, parse_weight


def make_payload(**overrides) -> ShipmentCreate:
    data = dict(origin="shymkent", destination="tashkent", cargo_category=CargoCategory.CLOTHING,
                weight=Decimal("150"), volume=Decimal("1.2"), packages=10, transport_type=TransportType.ROAD,
                desired_date=date.today() + timedelta(days=1), contact_phone="+77011234567")
    data.update(overrides)
    return ShipmentCreate(**data)


# 1. Создание пользователя
async def test_user_created_once(session):
    user, created = await get_or_create_user(session, 555, "nick", "Name")
    again, created_again = await get_or_create_user(session, 555, "new_nick", "Name")
    assert created and not created_again
    assert user.id == again.id and again.username == "new_nick"
    assert await session.scalar(select(User).where(User.telegram_id == 555)) is not None


# 2. Создание поставки
async def test_create_shipment(session, user):
    shipment, quote = await create_shipment(session, user, make_payload())
    assert shipment.id and shipment.user_id == user.id
    assert shipment.status == ShipmentStatus.PENDING
    assert shipment.estimated_price == quote.total > 0
    assert is_valid_tracking_number(shipment.tracking_number)
    history = list(await session.scalars(select(ShipmentHistory).where(ShipmentHistory.shipment_id == shipment.id)))
    assert [h.new_status for h in history] == [ShipmentStatus.CREATED, ShipmentStatus.PENDING]
    assert user.phone == "+77011234567"


# 3. Уникальный Tracking ID
def test_tracking_number_format():
    numbers = [generate_tracking_number(date(2026, 11, 6)) for _ in range(1000)]
    assert all(is_valid_tracking_number(n) and n.startswith("QDM-261106-") for n in numbers)
    assert len(set(numbers)) > 990  # 31^5 ≈ 28,6 млн вариантов в день
    assert normalize_tracking_number(" qdm2611067kx4p ") == "QDM-261106-7KX4P"
    assert not is_valid_tracking_number("QDM-261106-0O1IL")  # похожие символы исключены


async def test_tracking_numbers_unique_in_db(session, user):
    shipments = [(await create_shipment(session, user, make_payload()))[0] for _ in range(20)]
    assert len({s.tracking_number for s in shipments}) == 20


async def test_tracking_collision_is_retried(session, user, monkeypatch):
    first, _ = await create_shipment(session, user, make_payload())
    queue = iter([first.tracking_number, first.tracking_number, "QDM-261106-NEW22"])
    monkeypatch.setattr(shipment_service, "generate_tracking_number", lambda: next(queue))
    second, _ = await create_shipment(session, user, make_payload())
    assert second.tracking_number == "QDM-261106-NEW22"


# 5–6. Некорректный вес и объём
@pytest.mark.parametrize("raw", ["-5", "0", "abc", "", "1e5", "70000"])
def test_invalid_weight(raw):
    with pytest.raises(InputError):
        parse_weight(raw)


@pytest.mark.parametrize("raw", ["-1", "0", "0.0001", "x", "1000"])
def test_invalid_volume(raw):
    with pytest.raises(InputError):
        parse_volume(raw)


def test_valid_inputs():
    assert parse_weight("150 кг") == Decimal("150.00")
    assert parse_weight("1 250,5") == Decimal("1250.50")
    assert parse_volume("1,2 м3") == Decimal("1.200")
    assert parse_packages("10") == 10
    with pytest.raises(InputError):
        parse_packages("2.5")


def test_negative_values_rejected_by_model():
    with pytest.raises(ValidationError):
        make_payload(weight=Decimal("-10"))
    with pytest.raises(ValidationError):
        make_payload(volume=Decimal("0"))
    with pytest.raises(ValidationError):
        make_payload(destination="shymkent")


async def test_db_constraint_blocks_negative_weight(session, user):
    from sqlalchemy.exc import IntegrityError

    session.add(Shipment(tracking_number="QDM-000000-AAAAA", user_id=user.id, origin="shymkent",
                         destination="tashkent", cargo_category=CargoCategory.OTHER, weight=Decimal("-1"),
                         volume=Decimal("1"), packages=1, transport_type=TransportType.ROAD,
                         estimated_price=Decimal("1")))
    with pytest.raises(IntegrityError):
        await session.commit()
    await session.rollback()


def test_phone_and_date_validation():
    assert normalize_phone("8 701 123-45-67") == "+77011234567"
    assert normalize_phone("+998 90 123 45 67") == "+998901234567"
    with pytest.raises(InputError):
        normalize_phone("12345")
    today = date(2026, 11, 6)
    assert parse_date("25.11.2026", today) == date(2026, 11, 25)
    with pytest.raises(InputError):
        parse_date("01.01.2020", today)
    with pytest.raises(InputError):
        parse_date("завтра", today)


# 9. Ограничение доступа к чужим поставкам
async def test_foreign_shipment_access_denied(session, user, other_user):
    shipment, _ = await create_shipment(session, user, make_payload())
    assert (await get_shipment_for_user(session, user, shipment_id=shipment.id)).id == shipment.id
    with pytest.raises(AccessDeniedError):
        await get_shipment_for_user(session, other_user, shipment_id=shipment.id)
    with pytest.raises(AccessDeniedError):
        await get_shipment_for_user(session, other_user, tracking_number=shipment.tracking_number)
    # администратор видит любую поставку
    assert await get_shipment_for_user(session, other_user, shipment_id=shipment.id, is_admin=True)
    with pytest.raises(AccessDeniedError):
        await shipment_service.cancel_by_user(session, other_user, shipment.id)


async def test_user_cancel_only_before_confirmation(session, user):
    from services.tracking_service import change_status

    s1, _ = await create_shipment(session, user, make_payload())
    change = await shipment_service.cancel_by_user(session, user, s1.id)
    assert change.new_status == ShipmentStatus.CANCELLED

    s2, _ = await create_shipment(session, user, make_payload())
    await change_status(session, s2.id, ShipmentStatus.CONFIRMED)
    with pytest.raises(shipment_service.CannotCancelError):
        await shipment_service.cancel_by_user(session, user, s2.id)


async def test_shipment_not_found(session, user):
    with pytest.raises(shipment_service.ShipmentNotFoundError):
        await get_shipment_for_user(session, user, tracking_number="QDM-000000-ZZZZZ")
