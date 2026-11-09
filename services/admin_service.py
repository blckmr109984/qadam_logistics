"""Операции администратора: статистика, списки заявок, управление тарифами."""
from __future__ import annotations

import logging
from dataclasses import dataclass
from decimal import Decimal

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from database.models import Route, Shipment, ShipmentStatus, Tariff, User
from services.tracking_service import ACTIVE_STATUSES

logger = logging.getLogger(__name__)

TARIFF_FIELDS = {
    "base_price": "Базовая стоимость маршрута",
    "price_per_kg": "Цена за 1 кг",
    "price_per_m3": "Цена за 1 м³",
    "additional_cost": "Дополнительные расходы",
}


@dataclass(frozen=True, slots=True)
class Stats:
    users: int
    shipments: int
    active: int
    pending: int
    delivered: int
    cancelled: int


async def get_stats(session: AsyncSession) -> Stats:
    users = await session.scalar(select(func.count()).select_from(User)) or 0
    rows = (await session.execute(select(Shipment.status, func.count()).group_by(Shipment.status))).all()
    by_status = {ShipmentStatus(status): count for status, count in rows}
    return Stats(
        users=int(users),
        shipments=sum(by_status.values()),
        active=sum(c for s, c in by_status.items() if s in ACTIVE_STATUSES),
        pending=by_status.get(ShipmentStatus.PENDING, 0),
        delivered=by_status.get(ShipmentStatus.DELIVERED, 0),
        cancelled=by_status.get(ShipmentStatus.CANCELLED, 0),
    )


def _shipments_filter(scope: str):
    if scope == "new":
        return Shipment.status == ShipmentStatus.PENDING
    if scope == "active":
        return Shipment.status.in_(ACTIVE_STATUSES)
    return None


async def list_shipments(session: AsyncSession, scope: str = "all", limit: int = 8, offset: int = 0) -> list[Shipment]:
    query = select(Shipment).order_by(Shipment.created_at.desc(), Shipment.id.desc()).limit(limit).offset(offset)
    condition = _shipments_filter(scope)
    if condition is not None:
        query = query.where(condition)
    return list(await session.scalars(query))


async def count_shipments(session: AsyncSession, scope: str = "all") -> int:
    query = select(func.count()).select_from(Shipment)
    condition = _shipments_filter(scope)
    if condition is not None:
        query = query.where(condition)
    return int(await session.scalar(query) or 0)


async def list_tariffs(session: AsyncSession) -> list[Tariff]:
    rows = await session.scalars(
        select(Tariff).join(Route).options(selectinload(Tariff.route)).order_by(Route.origin, Route.destination, Tariff.transport_type)
    )
    return list(rows)


async def get_tariff(session: AsyncSession, tariff_id: int) -> Tariff | None:
    return await session.scalar(select(Tariff).options(selectinload(Tariff.route)).where(Tariff.id == tariff_id))


async def update_tariff_field(
    session: AsyncSession, tariff_id: int, field: str, value: Decimal, admin_id: int
) -> Tariff:
    if field not in TARIFF_FIELDS:
        raise ValueError(f"Unknown tariff field: {field}")
    if value < 0:
        raise ValueError("Tariff value must be non-negative")
    tariff = await get_tariff(session, tariff_id)
    if tariff is None:
        raise LookupError(tariff_id)
    old = getattr(tariff, field)
    setattr(tariff, field, value)
    await session.commit()
    await session.refresh(tariff)
    logger.info("Admin %s changed tariff %s.%s: %s -> %s", admin_id, tariff_id, field, old, value)
    return tariff


async def toggle_tariff(session: AsyncSession, tariff_id: int, admin_id: int) -> Tariff:
    tariff = await get_tariff(session, tariff_id)
    if tariff is None:
        raise LookupError(tariff_id)
    tariff.is_active = not tariff.is_active
    await session.commit()
    await session.refresh(tariff)
    logger.info("Admin %s set tariff %s active=%s", admin_id, tariff_id, tariff.is_active)
    return tariff
