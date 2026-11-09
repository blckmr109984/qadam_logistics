"""Статусы поставки: допустимые переходы, смена статуса, история.

В MVP статусы меняет администратор вручную — фиктивного GPS нет.
Смена статуса атомарна: UPDATE ... WHERE status = <ожидаемый старый статус>,
поэтому двойное нажатие кнопки или устаревшая кнопка не применят переход дважды.
"""
from __future__ import annotations

from dataclasses import dataclass

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from database.models import Shipment, ShipmentHistory, ShipmentStatus, utcnow
from utils.catalog import is_international

S = ShipmentStatus

# Основная цепочка этапов (для временной шкалы)
STATUS_FLOW: list[ShipmentStatus] = [
    S.CREATED, S.PENDING, S.CONFIRMED, S.PREPARING, S.PICKED_UP,
    S.IN_TRANSIT, S.AT_CUSTOMS, S.CUSTOMS_CLEARED, S.ARRIVED, S.DELIVERED,
]
CUSTOMS_STATUSES = {S.AT_CUSTOMS, S.CUSTOMS_CLEARED}
FINAL_STATUSES = {S.DELIVERED, S.CANCELLED}
ACTIVE_STATUSES = [s for s in S if s not in FINAL_STATUSES]
USER_CANCELLABLE = {S.CREATED, S.PENDING}

ALLOWED_TRANSITIONS: dict[ShipmentStatus, set[ShipmentStatus]] = {
    S.CREATED: {S.PENDING, S.CANCELLED},
    S.PENDING: {S.CONFIRMED, S.CANCELLED},
    S.CONFIRMED: {S.PREPARING, S.CANCELLED},
    S.PREPARING: {S.PICKED_UP, S.CANCELLED},
    S.PICKED_UP: {S.IN_TRANSIT, S.CANCELLED},
    S.IN_TRANSIT: {S.AT_CUSTOMS, S.ARRIVED, S.CANCELLED},
    S.AT_CUSTOMS: {S.CUSTOMS_CLEARED, S.CANCELLED},
    S.CUSTOMS_CLEARED: {S.ARRIVED},
    S.ARRIVED: {S.DELIVERED},
    S.DELIVERED: set(),
    S.CANCELLED: set(),
}


class TrackingError(Exception):
    pass


class InvalidTransitionError(TrackingError):
    def __init__(self, old: ShipmentStatus, new: ShipmentStatus) -> None:
        super().__init__(f"Transition {old} -> {new} is not allowed")
        self.old, self.new = old, new


class StaleStatusError(TrackingError):
    """Статус уже изменился (повторное нажатие или параллельное изменение)."""


@dataclass(frozen=True, slots=True)
class StatusChange:
    shipment: Shipment
    old_status: ShipmentStatus
    new_status: ShipmentStatus
    history: ShipmentHistory


def flow_for(shipment: Shipment) -> list[ShipmentStatus]:
    """Этапы для конкретной поставки: внутри одной страны таможня не нужна."""
    if is_international(shipment.origin, shipment.destination):
        return list(STATUS_FLOW)
    return [s for s in STATUS_FLOW if s not in CUSTOMS_STATUSES]


def allowed_next_statuses(shipment: Shipment) -> list[ShipmentStatus]:
    allowed = ALLOWED_TRANSITIONS[ShipmentStatus(shipment.status)]
    if not is_international(shipment.origin, shipment.destination):
        allowed = allowed - CUSTOMS_STATUSES
    order = STATUS_FLOW + [S.CANCELLED]
    return [s for s in order if s in allowed]


def can_transition(shipment: Shipment, new_status: ShipmentStatus) -> bool:
    return new_status in allowed_next_statuses(shipment)


async def add_history(
    session: AsyncSession,
    shipment_id: int,
    old_status: ShipmentStatus | None,
    new_status: ShipmentStatus,
    comment: str | None = None,
    changed_by: int | None = None,
) -> ShipmentHistory:
    record = ShipmentHistory(
        shipment_id=shipment_id,
        old_status=old_status,
        new_status=new_status,
        comment=comment,
        changed_by=changed_by,
    )
    session.add(record)
    await session.flush()
    return record


async def change_status(
    session: AsyncSession,
    shipment_id: int,
    new_status: ShipmentStatus,
    *,
    comment: str | None = None,
    changed_by: int | None = None,
    expected_old: ShipmentStatus | None = None,
    commit: bool = True,
) -> StatusChange:
    shipment = await session.get(Shipment, shipment_id)
    if shipment is None:
        from services.shipment_service import ShipmentNotFoundError

        raise ShipmentNotFoundError(shipment_id)

    old_status = ShipmentStatus(shipment.status)
    if expected_old is not None and old_status != expected_old:
        raise StaleStatusError(f"Expected {expected_old}, actual {old_status}")
    if not can_transition(shipment, new_status):
        raise InvalidTransitionError(old_status, new_status)

    # Условное обновление защищает от гонок между параллельными нажатиями.
    result = await session.execute(
        update(Shipment)
        .where(Shipment.id == shipment_id, Shipment.status == old_status)
        .values(status=new_status, updated_at=utcnow())
        .execution_options(synchronize_session=False)
    )
    if result.rowcount != 1:
        await session.rollback()
        raise StaleStatusError("Status was changed concurrently")

    record = await add_history(session, shipment_id, old_status, new_status, comment, changed_by)
    if commit:
        await session.commit()
    await session.refresh(shipment)
    return StatusChange(shipment=shipment, old_status=old_status, new_status=new_status, history=record)


async def get_history(session: AsyncSession, shipment_id: int) -> list[ShipmentHistory]:
    rows = await session.scalars(
        select(ShipmentHistory).where(ShipmentHistory.shipment_id == shipment_id).order_by(ShipmentHistory.id)
    )
    return list(rows)
