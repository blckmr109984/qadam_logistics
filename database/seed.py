"""Демонстрационные маршруты и ТЕСТОВЫЕ тарифы.

ВНИМАНИЕ: цифры ниже не являются рыночными ценами. Это условные тестовые
значения для демонстрации MVP. Расстояния — ориентировочные. Администратор
меняет тарифы прямо в боте (раздел /admin → Тарифы).
"""
from __future__ import annotations

import logging
from decimal import Decimal

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from database.models import Route, Tariff, TransportType
from utils.catalog import is_international

logger = logging.getLogger(__name__)

# (откуда, куда, ориентировочное расстояние в км, есть ли ж/д тариф)
DEMO_ROUTES: list[tuple[str, str, int, bool]] = [
    ("shymkent", "tashkent", 120, True),
    ("shymkent", "almaty", 690, True),
    ("shymkent", "astana", 1450, True),
    ("shymkent", "samarkand", 420, True),
    ("shymkent", "bishkek", 480, False),
    ("tashkent", "almaty", 810, True),
]


def _round100(value: float) -> Decimal:
    return Decimal(int(round(value / 100.0)) * 100)


def build_test_tariff(distance_km: int, transport: TransportType, international: bool) -> dict[str, Decimal]:
    """Условная формула генерации тестовых тарифов (только для демо-данных)."""
    if transport is TransportType.ROAD:
        base = _round100(10_000 + 40 * distance_km)
        per_kg = Decimal(round(25 + distance_km * 0.02))
        per_m3 = _round100(5_000 + distance_km * 5)
        additional = Decimal(7_000 if international else 0)
    else:
        base = _round100(20_000 + 25 * distance_km)
        per_kg = Decimal(round((25 + distance_km * 0.02) * 0.7))
        per_m3 = _round100((5_000 + distance_km * 5) * 0.7)
        additional = Decimal(10_000 if international else 3_000)
    return {"base_price": base, "price_per_kg": per_kg, "price_per_m3": per_m3, "additional_cost": additional}


async def seed_demo_data(session: AsyncSession) -> bool:
    """Заполняет маршруты и тарифы, если таблица маршрутов пуста. Возвращает True, если данные добавлены."""
    count = await session.scalar(select(func.count()).select_from(Route))
    if count:
        return False

    for origin, destination, distance, has_rail in DEMO_ROUTES:
        for a, b in ((origin, destination), (destination, origin)):
            route = Route(origin=a, destination=b, distance_km=distance, is_active=True)
            session.add(route)
            intl = is_international(a, b)
            transports = [TransportType.ROAD] + ([TransportType.RAIL] if has_rail else [])
            for transport in transports:
                route.tariffs.append(Tariff(transport_type=transport, is_active=True,
                                            **build_test_tariff(distance, transport, intl)))
    await session.commit()
    logger.info("Demo routes and TEST tariffs seeded")
    return True
