"""Поставки: создание, получение с проверкой доступа, списки, отмена клиентом."""
from __future__ import annotations

import logging
from datetime import date
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator
from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from database.models import CargoCategory, Shipment, ShipmentStatus, TransportType, User
from services import tracking_service
from services.pricing_service import PriceQuote, get_quote
from utils.tracking_id import generate_tracking_number, normalize_tracking_number
from utils.validators import MAX_PACKAGES, MAX_VOLUME_M3, MAX_WEIGHT_KG, normalize_phone

logger = logging.getLogger(__name__)


class ShipmentError(Exception):
    pass


class ShipmentNotFoundError(ShipmentError):
    pass


class AccessDeniedError(ShipmentError):
    pass


class CannotCancelError(ShipmentError):
    pass


class ShipmentCreate(BaseModel):
    """Валидированные данные заявки (последний рубеж проверки перед записью в БД)."""

    model_config = ConfigDict(frozen=True)

    origin: str = Field(min_length=2, max_length=32)
    destination: str = Field(min_length=2, max_length=32)
    cargo_category: CargoCategory
    weight: Decimal = Field(gt=0, le=MAX_WEIGHT_KG)
    volume: Decimal = Field(gt=0, le=MAX_VOLUME_M3)
    packages: int = Field(gt=0, le=MAX_PACKAGES)
    transport_type: TransportType
    desired_date: date | None = None
    contact_phone: str | None = None

    @field_validator("contact_phone")
    @classmethod
    def _phone(cls, value: str | None) -> str | None:
        return normalize_phone(value) if value else None

    @model_validator(mode="after")
    def _different_cities(self) -> ShipmentCreate:
        if self.origin == self.destination:
            raise ValueError("Origin and destination must differ")
        return self


async def _unique_tracking_number(session: AsyncSession, attempts: int = 10) -> str:
    for _ in range(attempts):
        number = generate_tracking_number()
        exists = await session.scalar(select(Shipment.id).where(Shipment.tracking_number == number))
        if exists is None:
            return number
    raise ShipmentError("Could not generate unique tracking number")


async def create_shipment(session: AsyncSession, user: User, data: ShipmentCreate) -> tuple[Shipment, PriceQuote]:
    """Создаёт поставку: расчёт по тарифу из БД, уникальный номер, история статусов."""
    quote = await get_quote(session, data.origin, data.destination, data.transport_type, data.weight, data.volume)

    for attempt in range(3):
        tracking = await _unique_tracking_number(session)
        shipment = Shipment(
            tracking_number=tracking,
            user_id=user.id,
            route_id=quote.route_id,
            origin=data.origin,
            destination=data.destination,
            cargo_category=data.cargo_category,
            weight=data.weight,
            volume=data.volume,
            packages=data.packages,
            transport_type=data.transport_type,
            desired_date=data.desired_date,
            contact_phone=data.contact_phone,
            estimated_price=quote.total,
            status=ShipmentStatus.PENDING,
        )
        session.add(shipment)
        try:
            await session.flush()
        except IntegrityError:  # крайне маловероятная коллизия номера — пробуем снова
            await session.rollback()
            logger.warning("Tracking number collision, retry %s", attempt + 1)
            continue

        await tracking_service.add_history(session, shipment.id, None, ShipmentStatus.CREATED, "Заявка создана клиентом")
        await tracking_service.add_history(
            session, shipment.id, ShipmentStatus.CREATED, ShipmentStatus.PENDING, "Передана на подтверждение"
        )
        if data.contact_phone and not user.phone:
            user.phone = data.contact_phone
        await session.commit()
        await session.refresh(shipment)
        logger.info("Shipment %s created by user %s", shipment.tracking_number, user.telegram_id)
        return shipment, quote

    raise ShipmentError("Failed to create shipment")


async def get_shipment(session: AsyncSession, shipment_id: int) -> Shipment:
    shipment = await session.get(Shipment, shipment_id)
    if shipment is None:
        raise ShipmentNotFoundError(shipment_id)
    return shipment


async def get_by_tracking(session: AsyncSession, tracking_number: str) -> Shipment:
    number = normalize_tracking_number(tracking_number)
    shipment = await session.scalar(select(Shipment).where(Shipment.tracking_number == number))
    if shipment is None:
        raise ShipmentNotFoundError(number)
    return shipment


def ensure_access(shipment: Shipment, user: User, is_admin: bool = False) -> None:
    """Клиент видит только свои поставки; администратор — все."""
    if not is_admin and shipment.user_id != user.id:
        raise AccessDeniedError(shipment.id)


async def get_shipment_for_user(
    session: AsyncSession, user: User, *, shipment_id: int | None = None,
    tracking_number: str | None = None, is_admin: bool = False,
) -> Shipment:
    if shipment_id is not None:
        shipment = await get_shipment(session, shipment_id)
    elif tracking_number is not None:
        shipment = await get_by_tracking(session, tracking_number)
    else:
        raise ValueError("shipment_id or tracking_number is required")
    ensure_access(shipment, user, is_admin)
    return shipment


async def list_user_shipments(session: AsyncSession, user: User, limit: int = 5, offset: int = 0) -> list[Shipment]:
    rows = await session.scalars(
        select(Shipment)
        .where(Shipment.user_id == user.id)
        .order_by(Shipment.created_at.desc(), Shipment.id.desc())
        .limit(limit)
        .offset(offset)
    )
    return list(rows)


async def count_user_shipments(session: AsyncSession, user: User) -> int:
    return int(await session.scalar(select(func.count()).where(Shipment.user_id == user.id)) or 0)


async def cancel_by_user(session: AsyncSession, user: User, shipment_id: int) -> tracking_service.StatusChange:
    shipment = await get_shipment_for_user(session, user, shipment_id=shipment_id)
    status = ShipmentStatus(shipment.status)
    if status not in tracking_service.USER_CANCELLABLE:
        raise CannotCancelError(status)
    return await tracking_service.change_status(
        session, shipment.id, ShipmentStatus.CANCELLED,
        comment="Отменена клиентом", changed_by=user.telegram_id, expected_old=status,
    )
