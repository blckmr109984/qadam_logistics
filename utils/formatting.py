"""Оформление сообщений: карточка поставки, временная шкала, разбивка стоимости."""
from __future__ import annotations

from datetime import date, datetime, timedelta
from decimal import Decimal
from html import escape
from typing import Any

from config import get_settings
from database.models import CargoCategory, Shipment, ShipmentHistory, ShipmentStatus, TransportType
from i18n import t
from services.pricing_service import PriceQuote
from services.tracking_service import flow_for
from utils.catalog import CATEGORY_EMOJI, STATUS_EMOJI, TRANSPORT_EMOJI, city_label

DIVIDER = "━━━━━━━━━━━━━━━━"


def money(value: Decimal | int | float) -> str:
    amount = int(Decimal(value).quantize(Decimal("1")))
    return f"{amount:,}".replace(",", " ") + f" {get_settings().currency}"


def number(value: Decimal | int | float | str) -> str:
    """150.00 -> '150', 1.200 -> '1.2'."""
    dec = Decimal(str(value))
    text = format(dec.normalize(), "f")
    return text


def local_dt(value: datetime | None) -> str:
    if value is None:
        return "—"
    return (value + timedelta(hours=get_settings().tz_offset_hours)).strftime("%d.%m.%Y %H:%M")


def local_today() -> date:
    from database.models import utcnow

    return (utcnow() + timedelta(hours=get_settings().tz_offset_hours)).date()


def status_label(status: ShipmentStatus | str, lang: str) -> str:
    status = ShipmentStatus(status)
    return f"{STATUS_EMOJI[status]} {t(lang, f'status_{status.value}')}"


def category_label(category: CargoCategory | str, lang: str) -> str:
    category = CargoCategory(category)
    return f"{CATEGORY_EMOJI[category]} {t(lang, f'cat_{category.value}')}"


def transport_label(transport: TransportType | str, lang: str) -> str:
    transport = TransportType(transport)
    return f"{TRANSPORT_EMOJI[transport]} {t(lang, f'tr_{transport.value}')}"


def route_label(origin: str, destination: str, lang: str) -> str:
    return f"{city_label(origin, lang)} → {city_label(destination, lang)}"


def price_breakdown(quote: PriceQuote, lang: str, footer: bool = True) -> str:
    weight_line = t(lang, "price_weight", weight=number(quote.weight), rate=money(quote.price_per_kg))
    volume_line = t(lang, "price_volume", volume=number(quote.volume), rate=money(quote.price_per_m3))
    mark = f"  <b>{t(lang, 'price_applied')}</b>"
    lines = [
        t(lang, "price_title") + f" · {transport_label(quote.transport_type, lang)}",
        f"{route_label(quote.origin, quote.destination, lang)} · {quote.distance_km} {t(lang, 'unit_km')}",
        "",
        f"▫️ {t(lang, 'price_base')}: <b>{money(quote.base_price)}</b>",
        f"▫️ {weight_line} = {money(quote.weight_cost)}" + (mark if quote.chargeable_basis == "weight" else ""),
        f"▫️ {volume_line} = {money(quote.volume_cost)}" + (mark if quote.chargeable_basis == "volume" else ""),
        f"▫️ {t(lang, 'price_additional')}: {money(quote.additional_cost)}",
        DIVIDER,
        f"🟠 <b>{t(lang, 'price_total')}: {money(quote.total)}</b>",
    ]
    if footer:
        lines += ["", t(lang, "price_rule"), t(lang, "price_disclaimer")]
    return "\n".join(lines)


def compact_quote_line(quote: PriceQuote, lang: str) -> str:
    return f"{transport_label(quote.transport_type, lang)} — <b>{money(quote.total)}</b>"


def draft_summary(data: dict[str, Any], lang: str) -> str:
    """Короткая строка с уже заполненными полями (видна на каждом шаге оформления)."""
    parts: list[str] = []
    if data.get("origin"):
        dest = city_label(data["destination"], lang) if data.get("destination") else "…"
        parts.append(f"{city_label(data['origin'], lang)} → {dest}")
    if data.get("category"):
        parts.append(category_label(data["category"], lang))
    if data.get("weight"):
        parts.append(f"{number(data['weight'])} {t(lang, 'unit_kg')}")
    if data.get("volume"):
        parts.append(f"{number(data['volume'])} {t(lang, 'unit_m3')}")
    if data.get("packages"):
        parts.append(f"{data['packages']} {t(lang, 'unit_pcs')}")
    if data.get("transport"):
        parts.append(transport_label(data["transport"], lang))
    if data.get("date"):
        parts.append(f"📅 {date.fromisoformat(data['date']):%d.%m.%Y}")
    return "<i>" + " · ".join(parts) + "</i>" if parts else ""


def draft_details(data: dict[str, Any], lang: str) -> str:
    """Полная сводка черновика заявки (шаг подтверждения)."""
    na = t(lang, "not_specified")
    rows = [
        (t(lang, "f_route"), route_label(data["origin"], data["destination"], lang)
         if data.get("origin") and data.get("destination") else na),
        (t(lang, "f_category"), category_label(data["category"], lang) if data.get("category") else na),
        (t(lang, "f_weight"), f"{number(data['weight'])} {t(lang, 'unit_kg')}" if data.get("weight") else na),
        (t(lang, "f_volume"), f"{number(data['volume'])} {t(lang, 'unit_m3')}" if data.get("volume") else na),
        (t(lang, "f_packages"), f"{data['packages']} {t(lang, 'unit_pcs')}" if data.get("packages") else na),
        (t(lang, "f_transport"), transport_label(data["transport"], lang) if data.get("transport") else na),
        (t(lang, "f_date"), f"{date.fromisoformat(data['date']):%d.%m.%Y}" if data.get("date") else na),
        (t(lang, "f_phone"), escape(data["phone"]) if data.get("phone") else na),
    ]
    return "\n".join(f"<b>{label}:</b> {value}" for label, value in rows)


def extracted_details(data: dict[str, Any], lang: str) -> str:
    """Сводка данных, распознанных AI (✅ — найдено, ▫️ — не указано)."""
    na = t(lang, "not_specified")

    def row(ok: bool, label: str, value: str) -> str:
        return f"{'✅' if ok else '▫️'} <b>{label}:</b> {value if ok else na}"

    return "\n".join([
        row(bool(data.get("origin")), t(lang, "f_origin"), city_label(data.get("origin", ""), lang)),
        row(bool(data.get("destination")), t(lang, "f_destination"), city_label(data.get("destination", ""), lang)),
        row(bool(data.get("category")), t(lang, "f_category"),
            category_label(data["category"], lang) if data.get("category") else ""),
        row(bool(data.get("weight")), t(lang, "f_weight"),
            f"{number(data['weight'])} {t(lang, 'unit_kg')}" if data.get("weight") else ""),
        row(bool(data.get("volume")), t(lang, "f_volume"),
            f"{number(data['volume'])} {t(lang, 'unit_m3')}" if data.get("volume") else ""),
        row(bool(data.get("packages")), t(lang, "f_packages"),
            f"{data['packages']} {t(lang, 'unit_pcs')}" if data.get("packages") else ""),
        row(bool(data.get("transport")), t(lang, "f_transport"),
            transport_label(data["transport"], lang) if data.get("transport") else ""),
    ])


def timeline(shipment: Shipment, lang: str) -> str:
    """Визуальная шкала: ✅ пройдено · 🟠 текущий этап · ⚪️ впереди."""
    current = ShipmentStatus(shipment.status)
    lines = [t(lang, "timeline_title")]
    if current is ShipmentStatus.CANCELLED:
        lines.append(f"❌ <b>{t(lang, 'status_cancelled')}</b>")
        return "\n".join(lines)
    flow = flow_for(shipment)
    current_index = flow.index(current) if current in flow else 0
    for index, status in enumerate(flow):
        label = t(lang, f"status_{status.value}")
        if index < current_index or (status is ShipmentStatus.DELIVERED and current is ShipmentStatus.DELIVERED):
            lines.append(f"✅ {label}")
        elif index == current_index:
            lines.append(f"🟠 <b>{label}</b>")
        else:
            lines.append(f"⚪️ {label}")
        if index < len(flow) - 1:
            lines.append("┃" if index < current_index else "┆")
    return "\n".join(lines)


def shipment_card(shipment: Shipment, lang: str, with_timeline: bool = True) -> str:
    unit_kg, unit_m3, unit_pcs = t(lang, "unit_kg"), t(lang, "unit_m3"), t(lang, "unit_pcs")
    lines = [
        t(lang, "card_title", tracking=shipment.tracking_number),
        DIVIDER,
        f"<b>{t(lang, 'f_route')}:</b> {route_label(shipment.origin, shipment.destination, lang)}",
        f"<b>{t(lang, 'f_category')}:</b> {category_label(shipment.cargo_category, lang)}",
        f"<b>{t(lang, 'f_weight')}:</b> {number(shipment.weight)} {unit_kg}  ·  "
        f"<b>{t(lang, 'f_volume')}:</b> {number(shipment.volume)} {unit_m3}",
        f"<b>{t(lang, 'f_packages')}:</b> {shipment.packages} {unit_pcs}",
        f"<b>{t(lang, 'f_transport')}:</b> {transport_label(shipment.transport_type, lang)}",
    ]
    if shipment.desired_date:
        lines.append(f"<b>{t(lang, 'f_date')}:</b> {shipment.desired_date:%d.%m.%Y}")
    lines += [
        f"<b>{t(lang, 'f_price')}:</b> 🟠 {money(shipment.estimated_price)}",
        f"<b>{t(lang, 'f_status')}:</b> {status_label(shipment.status, lang)}",
        f"<b>{t(lang, 'f_created')}:</b> {local_dt(shipment.created_at)}",
        f"<b>{t(lang, 'f_updated')}:</b> {local_dt(shipment.updated_at)}",
    ]
    if with_timeline:
        lines += ["", timeline(shipment, lang)]
    return "\n".join(lines)


def history_text(shipment: Shipment, history: list[ShipmentHistory], lang: str) -> str:
    lines = [t(lang, "history_title", tracking=shipment.tracking_number), DIVIDER]
    if not history:
        lines.append(t(lang, "history_empty"))
    for record in history:
        lines.append(f"<b>{local_dt(record.created_at)}</b>")
        lines.append(f"   {status_label(record.new_status, lang)}")
    return "\n".join(lines)


def status_notification(shipment: Shipment, old: ShipmentStatus, new: ShipmentStatus, lang: str,
                        comment: str | None = None) -> str:
    text = t(
        lang, "notify_status",
        tracking=shipment.tracking_number,
        route=route_label(shipment.origin, shipment.destination, lang),
        old=status_label(old, lang),
        new=status_label(new, lang),
    )
    if comment:
        text += "\n" + t(lang, "notify_comment", comment=escape(comment))
    return text


def admin_shipment_text(shipment: Shipment, owner, history: list[ShipmentHistory] | None = None,
                        title: str | None = None) -> str:
    """Карточка поставки для администратора (на русском) — с данными клиента и историей."""
    lines = [title, ""] if title else []
    lines.append(shipment_card(shipment, "ru", with_timeline=False))
    username = f" @{escape(owner.username)}" if getattr(owner, "username", None) else ""
    lines += [
        "",
        "<b>👤 Клиент</b>",
        f"{escape(owner.full_name or '—')}{username}",
        f"Telegram ID: <code>{owner.telegram_id}</code>",
        f"Телефон: {escape(shipment.contact_phone or owner.phone or '—')}",
    ]
    if history:
        lines += ["", "<b>🕓 История</b>"]
        for record in history[-8:]:
            comment = f" — <i>{escape(record.comment)}</i>" if record.comment else ""
            lines.append(f"{local_dt(record.created_at)} · {status_label(record.new_status, 'ru')}{comment}")
    return "\n".join(lines)
