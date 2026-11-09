"""Калькулятор предварительной стоимости.

Формула:
    Стоимость = Базовая стоимость маршрута
              + max(Вес × цена за кг, Объём × цена за м³)
              + Дополнительные расходы

Груз может «упираться» либо в вес (тяжёлый и компактный), либо в объём
(лёгкий и громоздкий), поэтому из двух расчётных величин берётся наибольшая.
Базовая стоимость задаётся для каждого маршрута отдельно и отражает расстояние.
Все тарифы берутся только из базы данных.
"""
from __future__ import annotations

from dataclasses import dataclass
from decimal import ROUND_HALF_UP, Decimal

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from database.models import Route, Tariff, TransportType


class PricingError(Exception):
    """Базовая ошибка расчёта."""


class RouteNotFoundError(PricingError):
    pass


class TariffNotFoundError(PricingError):
    pass


@dataclass(frozen=True, slots=True)
class PriceQuote:
    route_id: int
    tariff_id: int
    origin: str
    destination: str
    distance_km: int
    transport_type: TransportType
    weight: Decimal
    volume: Decimal
    base_price: Decimal
    price_per_kg: Decimal
    price_per_m3: Decimal
    weight_cost: Decimal
    volume_cost: Decimal
    chargeable_cost: Decimal
    chargeable_basis: str  # "weight" | "volume"
    additional_cost: Decimal
    total: Decimal


def _money(value: Decimal) -> Decimal:
    return value.quantize(Decimal("1"), rounding=ROUND_HALF_UP)


def calculate_quote(route: Route, tariff: Tariff, weight: Decimal, volume: Decimal) -> PriceQuote:
    """Чистая функция расчёта (без обращения к БД) — удобно тестировать."""
    weight = Decimal(weight)
    volume = Decimal(volume)
    if weight <= 0 or volume <= 0:
        raise PricingError("Weight and volume must be positive")

    base = Decimal(tariff.base_price)
    per_kg = Decimal(tariff.price_per_kg)
    per_m3 = Decimal(tariff.price_per_m3)
    additional = Decimal(tariff.additional_cost or 0)

    weight_cost = _money(weight * per_kg)
    volume_cost = _money(volume * per_m3)
    if volume_cost > weight_cost:
        chargeable, basis = volume_cost, "volume"
    else:
        chargeable, basis = weight_cost, "weight"

    total = _money(base + chargeable + additional)
    return PriceQuote(
        route_id=route.id,
        tariff_id=tariff.id,
        origin=route.origin,
        destination=route.destination,
        distance_km=route.distance_km,
        transport_type=TransportType(tariff.transport_type),
        weight=weight,
        volume=volume,
        base_price=_money(base),
        price_per_kg=per_kg,
        price_per_m3=per_m3,
        weight_cost=weight_cost,
        volume_cost=volume_cost,
        chargeable_cost=chargeable,
        chargeable_basis=basis,
        additional_cost=_money(additional),
        total=total,
    )


async def get_route(session: AsyncSession, origin: str, destination: str) -> Route | None:
    return await session.scalar(
        select(Route).where(Route.origin == origin, Route.destination == destination, Route.is_active.is_(True))
    )


async def get_tariff(session: AsyncSession, route_id: int, transport: TransportType) -> Tariff | None:
    return await session.scalar(
        select(Tariff).where(
            Tariff.route_id == route_id, Tariff.transport_type == transport, Tariff.is_active.is_(True)
        )
    )


async def get_quote(
    session: AsyncSession,
    origin: str,
    destination: str,
    transport: TransportType,
    weight: Decimal,
    volume: Decimal,
) -> PriceQuote:
    route = await get_route(session, origin, destination)
    if route is None:
        raise RouteNotFoundError(f"{origin}->{destination}")
    tariff = await get_tariff(session, route.id, transport)
    if tariff is None:
        raise TariffNotFoundError(f"{origin}->{destination} {transport}")
    return calculate_quote(route, tariff, weight, volume)


async def get_all_quotes(
    session: AsyncSession, origin: str, destination: str, weight: Decimal, volume: Decimal
) -> list[PriceQuote]:
    """Оценки по всем доступным видам транспорта на маршруте (для сравнения)."""
    route = await get_route(session, origin, destination)
    if route is None:
        raise RouteNotFoundError(f"{origin}->{destination}")
    tariffs = await session.scalars(
        select(Tariff).where(Tariff.route_id == route.id, Tariff.is_active.is_(True)).order_by(Tariff.transport_type)
    )
    quotes = [calculate_quote(route, t, weight, volume) for t in tariffs]
    if not quotes:
        raise TariffNotFoundError(f"{origin}->{destination}")
    return sorted(quotes, key=lambda q: q.total)


async def list_origins(session: AsyncSession) -> list[str]:
    """Города, из которых есть хотя бы один активный маршрут с активным тарифом."""
    rows = await session.scalars(
        select(Route.origin)
        .join(Tariff, Tariff.route_id == Route.id)
        .where(Route.is_active.is_(True), Tariff.is_active.is_(True))
        .distinct()
        .order_by(Route.origin)
    )
    return list(rows)


async def list_destinations(session: AsyncSession, origin: str) -> list[str]:
    rows = await session.scalars(
        select(Route.destination)
        .join(Tariff, Tariff.route_id == Route.id)
        .where(Route.origin == origin, Route.is_active.is_(True), Tariff.is_active.is_(True))
        .distinct()
        .order_by(Route.destination)
    )
    return list(rows)


async def list_transports(session: AsyncSession, origin: str, destination: str) -> list[TransportType]:
    route = await get_route(session, origin, destination)
    if route is None:
        return []
    rows = await session.scalars(
        select(Tariff.transport_type).where(Tariff.route_id == route.id, Tariff.is_active.is_(True))
    )
    order = [TransportType.ROAD, TransportType.RAIL]
    found = {TransportType(r) for r in rows}
    return [t for t in order if t in found]
