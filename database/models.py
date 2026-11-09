"""SQLAlchemy-модели Qadam Logistics."""
from __future__ import annotations

import enum
from datetime import UTC, date, datetime
from decimal import Decimal

from sqlalchemy import (
    BigInteger,
    Boolean,
    CheckConstraint,
    Date,
    DateTime,
    Enum,
    ForeignKey,
    Index,
    Integer,
    Numeric,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


def utcnow() -> datetime:
    """Текущее время в UTC без tzinfo (SQLite не хранит часовой пояс)."""
    return datetime.now(UTC).replace(tzinfo=None)


class Base(DeclarativeBase):
    pass


class Language(enum.StrEnum):
    RU = "ru"
    KK = "kk"
    EN = "en"


class TransportType(enum.StrEnum):
    ROAD = "road"
    RAIL = "rail"


class CargoCategory(enum.StrEnum):
    CLOTHING = "clothing"
    ELECTRONICS = "electronics"
    FOOD = "food"
    CONSTRUCTION = "construction"
    FURNITURE = "furniture"
    OTHER = "other"


class ShipmentStatus(enum.StrEnum):
    CREATED = "created"                  # 1. Заявка создана
    PENDING = "pending"                  # 2. Ожидает подтверждения
    CONFIRMED = "confirmed"              # 3. Подтверждена
    PREPARING = "preparing"              # 4. Подготовка груза
    PICKED_UP = "picked_up"              # 5. Груз принят перевозчиком
    IN_TRANSIT = "in_transit"            # 6. В пути
    AT_CUSTOMS = "at_customs"            # 7. Прибыл на таможенное оформление
    CUSTOMS_CLEARED = "customs_cleared"  # 8. Таможенное оформление завершено
    ARRIVED = "arrived"                  # 9. Прибыл в город назначения
    DELIVERED = "delivered"              # 10. Доставлен
    CANCELLED = "cancelled"              # 11. Отменён


def _enum(enum_cls: type[enum.Enum], name: str) -> Enum:
    """Enum хранится как строка (VARCHAR + CHECK) — одинаково для SQLite и PostgreSQL."""
    return Enum(
        enum_cls,
        name=name,
        native_enum=False,
        create_constraint=True,
        length=20,
        values_callable=lambda e: [m.value for m in e],
        validate_strings=True,
    )


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    telegram_id: Mapped[int] = mapped_column(BigInteger, unique=True, index=True, nullable=False)
    username: Mapped[str | None] = mapped_column(String(64))
    full_name: Mapped[str] = mapped_column(String(256), default="", nullable=False)
    phone: Mapped[str | None] = mapped_column(String(20))
    language: Mapped[Language] = mapped_column(_enum(Language, "language"), default=Language.RU, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow, nullable=False)

    shipments: Mapped[list[Shipment]] = relationship(back_populates="user", cascade="all, delete-orphan")

    def __repr__(self) -> str:
        return f"<User id={self.id} tg={self.telegram_id}>"


class Route(Base):
    __tablename__ = "routes"
    __table_args__ = (
        UniqueConstraint("origin", "destination", name="uq_route_origin_destination"),
        CheckConstraint("distance_km > 0", name="ck_route_distance_positive"),
        CheckConstraint("origin <> destination", name="ck_route_different_cities"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    origin: Mapped[str] = mapped_column(String(32), nullable=False, index=True)
    destination: Mapped[str] = mapped_column(String(32), nullable=False)
    distance_km: Mapped[int] = mapped_column(Integer, nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    tariffs: Mapped[list[Tariff]] = relationship(back_populates="route", cascade="all, delete-orphan")

    def __repr__(self) -> str:
        return f"<Route {self.origin}->{self.destination} {self.distance_km}km>"


class Tariff(Base):
    __tablename__ = "tariffs"
    __table_args__ = (
        UniqueConstraint("route_id", "transport_type", name="uq_tariff_route_transport"),
        CheckConstraint("base_price >= 0", name="ck_tariff_base_nonneg"),
        CheckConstraint("price_per_kg >= 0", name="ck_tariff_kg_nonneg"),
        CheckConstraint("price_per_m3 >= 0", name="ck_tariff_m3_nonneg"),
        CheckConstraint("additional_cost >= 0", name="ck_tariff_additional_nonneg"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    route_id: Mapped[int] = mapped_column(ForeignKey("routes.id", ondelete="CASCADE"), nullable=False, index=True)
    transport_type: Mapped[TransportType] = mapped_column(_enum(TransportType, "transport_type"), nullable=False)
    base_price: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)
    price_per_kg: Mapped[Decimal] = mapped_column(Numeric(10, 2), nullable=False)
    price_per_m3: Mapped[Decimal] = mapped_column(Numeric(10, 2), nullable=False)
    additional_cost: Mapped[Decimal] = mapped_column(Numeric(12, 2), default=Decimal("0"), nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow, onupdate=utcnow, nullable=False)

    route: Mapped[Route] = relationship(back_populates="tariffs")


class Shipment(Base):
    __tablename__ = "shipments"
    __table_args__ = (
        CheckConstraint("weight > 0", name="ck_shipment_weight_positive"),
        CheckConstraint("volume > 0", name="ck_shipment_volume_positive"),
        CheckConstraint("packages > 0", name="ck_shipment_packages_positive"),
        CheckConstraint("estimated_price >= 0", name="ck_shipment_price_nonneg"),
        Index("ix_shipments_status", "status"),
        Index("ix_shipments_user_created", "user_id", "created_at"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    tracking_number: Mapped[str] = mapped_column(String(20), unique=True, index=True, nullable=False)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    route_id: Mapped[int | None] = mapped_column(ForeignKey("routes.id", ondelete="SET NULL"))
    origin: Mapped[str] = mapped_column(String(32), nullable=False)
    destination: Mapped[str] = mapped_column(String(32), nullable=False)
    cargo_category: Mapped[CargoCategory] = mapped_column(_enum(CargoCategory, "cargo_category"), nullable=False)
    weight: Mapped[Decimal] = mapped_column(Numeric(10, 2), nullable=False)
    volume: Mapped[Decimal] = mapped_column(Numeric(10, 3), nullable=False)
    packages: Mapped[int] = mapped_column(Integer, nullable=False)
    transport_type: Mapped[TransportType] = mapped_column(_enum(TransportType, "transport_type"), nullable=False)
    desired_date: Mapped[date | None] = mapped_column(Date)
    contact_phone: Mapped[str | None] = mapped_column(String(20))
    estimated_price: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)
    status: Mapped[ShipmentStatus] = mapped_column(
        _enum(ShipmentStatus, "shipment_status"), default=ShipmentStatus.CREATED, nullable=False
    )
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow, onupdate=utcnow, nullable=False)

    user: Mapped[User] = relationship(back_populates="shipments")
    route: Mapped[Route | None] = relationship()
    history: Mapped[list[ShipmentHistory]] = relationship(
        back_populates="shipment", cascade="all, delete-orphan", order_by="ShipmentHistory.id"
    )

    def __repr__(self) -> str:
        return f"<Shipment {self.tracking_number} {self.status}>"


class ShipmentHistory(Base):
    __tablename__ = "shipment_history"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    shipment_id: Mapped[int] = mapped_column(
        ForeignKey("shipments.id", ondelete="CASCADE"), nullable=False, index=True
    )
    old_status: Mapped[ShipmentStatus | None] = mapped_column(_enum(ShipmentStatus, "shipment_status"))
    new_status: Mapped[ShipmentStatus] = mapped_column(_enum(ShipmentStatus, "shipment_status"), nullable=False)
    comment: Mapped[str | None] = mapped_column(Text)
    changed_by: Mapped[int | None] = mapped_column(BigInteger)  # Telegram ID того, кто изменил статус
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow, nullable=False)

    shipment: Mapped[Shipment] = relationship(back_populates="history")
