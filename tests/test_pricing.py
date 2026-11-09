from decimal import Decimal

import pytest

from database.models import Route, Tariff, TransportType
from services import admin_service
from services.pricing_service import (
    PricingError, RouteNotFoundError, TariffNotFoundError, calculate_quote, get_all_quotes, get_quote,
    list_destinations, list_origins, list_transports,
)


def _route_tariff(base=10000, per_kg=20, per_m3=5000, additional=1000):
    route = Route(id=1, origin="shymkent", destination="tashkent", distance_km=120, is_active=True)
    tariff = Tariff(id=1, route_id=1, transport_type=TransportType.ROAD, base_price=Decimal(base),
                    price_per_kg=Decimal(per_kg), price_per_m3=Decimal(per_m3),
                    additional_cost=Decimal(additional), is_active=True)
    return route, tariff


def test_heavy_cargo_charged_by_weight():
    route, tariff = _route_tariff()
    q = calculate_quote(route, tariff, Decimal("1000"), Decimal("1"))  # 20 000 по весу vs 5 000 по объёму
    assert q.chargeable_basis == "weight"
    assert q.weight_cost == Decimal("20000") and q.volume_cost == Decimal("5000")
    assert q.total == Decimal("31000")  # 10 000 + 20 000 + 1 000


def test_bulky_cargo_charged_by_volume():
    route, tariff = _route_tariff()
    q = calculate_quote(route, tariff, Decimal("100"), Decimal("3"))  # 2 000 по весу vs 15 000 по объёму
    assert q.chargeable_basis == "volume"
    assert q.chargeable_cost == Decimal("15000")
    assert q.total == Decimal("26000")


def test_fractional_values_rounded_to_whole_currency():
    route, tariff = _route_tariff(base=0, per_kg=Decimal("27"), per_m3=0, additional=0)
    q = calculate_quote(route, tariff, Decimal("10.55"), Decimal("0.1"))
    assert q.total == Decimal("285")  # 284.85 -> 285


def test_non_positive_values_rejected():
    route, tariff = _route_tariff()
    with pytest.raises(PricingError):
        calculate_quote(route, tariff, Decimal("0"), Decimal("1"))
    with pytest.raises(PricingError):
        calculate_quote(route, tariff, Decimal("10"), Decimal("-1"))


async def test_quote_uses_tariff_from_database(session):
    q = await get_quote(session, "shymkent", "tashkent", TransportType.ROAD, Decimal("150"), Decimal("1.2"))
    # Тестовый тариф: 14 800 + max(150×27=4 050; 1.2×5 600=6 720) + 7 000
    assert q.total == Decimal("28520")
    assert q.chargeable_basis == "volume"
    assert q.distance_km == 120


async def test_admin_tariff_change_affects_quote(session):
    q1 = await get_quote(session, "shymkent", "tashkent", TransportType.ROAD, Decimal("150"), Decimal("1.2"))
    await admin_service.update_tariff_field(session, q1.tariff_id, "base_price", Decimal("20000"), admin_id=1)
    q2 = await get_quote(session, "shymkent", "tashkent", TransportType.ROAD, Decimal("150"), Decimal("1.2"))
    assert q2.total - q1.total == Decimal("20000") - q1.base_price


async def test_admin_cannot_set_negative_tariff(session):
    q = await get_quote(session, "shymkent", "tashkent", TransportType.ROAD, Decimal("1"), Decimal("1"))
    with pytest.raises(ValueError):
        await admin_service.update_tariff_field(session, q.tariff_id, "price_per_kg", Decimal("-1"), admin_id=1)


async def test_unknown_route_and_disabled_tariff(session):
    with pytest.raises(RouteNotFoundError):
        await get_quote(session, "tashkent", "bishkek", TransportType.ROAD, Decimal("1"), Decimal("1"))
    with pytest.raises(TariffNotFoundError):  # на маршруте Шымкент—Бишкек нет ж/д тарифа
        await get_quote(session, "shymkent", "bishkek", TransportType.RAIL, Decimal("1"), Decimal("1"))

    q = await get_quote(session, "shymkent", "tashkent", TransportType.RAIL, Decimal("1"), Decimal("1"))
    await admin_service.toggle_tariff(session, q.tariff_id, admin_id=1)
    with pytest.raises(TariffNotFoundError):
        await get_quote(session, "shymkent", "tashkent", TransportType.RAIL, Decimal("1"), Decimal("1"))


async def test_route_catalog(session):
    assert "shymkent" in await list_origins(session)
    assert "tashkent" in await list_destinations(session, "shymkent")
    assert await list_transports(session, "shymkent", "bishkek") == [TransportType.ROAD]
    quotes = await get_all_quotes(session, "shymkent", "tashkent", Decimal("150"), Decimal("1.2"))
    assert len(quotes) == 2 and quotes[0].total <= quotes[1].total
