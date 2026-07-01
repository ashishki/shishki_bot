"""Database models for bookings, reminders, notifications, and finance."""

from __future__ import annotations

from datetime import UTC, datetime
from decimal import Decimal
from enum import StrEnum

from sqlalchemy import (
    BigInteger,
    Boolean,
    DateTime,
    ForeignKey,
    Integer,
    Numeric,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy import Enum as SAEnum
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


def utc_now() -> datetime:
    return datetime.now(UTC)


class Base(DeclarativeBase):
    pass


class BookingStatus(StrEnum):
    DRAFT = "draft"
    CONFIRMED = "confirmed"
    RESCHEDULED = "rescheduled"
    CANCELLED_BY_CLIENT = "cancelled_by_client"
    CANCELLED_BY_ADMIN = "cancelled_by_admin"
    COMPLETED = "completed"
    NO_SHOW = "no_show"


class DeliveryStatus(StrEnum):
    PENDING = "pending"
    PROCESSING = "processing"
    SENT = "sent"
    FAILED = "failed"
    SKIPPED = "skipped"


class ExpenseCategory(StrEnum):
    MATERIALS = "materials"
    RENT = "rent"
    ASSISTANT = "assistant"
    OTHER = "other"


class ReferralStatus(StrEnum):
    PENDING = "pending"
    QUALIFIED = "qualified"


class ReferralBonusStatus(StrEnum):
    PENDING = "pending"
    AWARDED = "awarded"


def enum_column(enum_type: type[StrEnum], name: str) -> SAEnum:
    return SAEnum(
        enum_type,
        name=name,
        native_enum=False,
        create_constraint=True,
        validate_strings=True,
        values_callable=lambda members: [member.value for member in members],
    )


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(primary_key=True)
    telegram_id: Mapped[int] = mapped_column(BigInteger, unique=True, nullable=False)
    username: Mapped[str | None] = mapped_column(String(255))
    display_name: Mapped[str | None] = mapped_column(String(255))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utc_now, nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utc_now, onupdate=utc_now, nullable=False
    )

    client: Mapped[Client | None] = relationship(back_populates="user")


class Client(Base):
    __tablename__ = "clients"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int | None] = mapped_column(ForeignKey("users.id"), unique=True)
    display_name: Mapped[str | None] = mapped_column(String(255))
    notes: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utc_now, nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utc_now, onupdate=utc_now, nullable=False
    )

    user: Mapped[User | None] = relationship(back_populates="client")
    bookings: Mapped[list[Booking]] = relationship(back_populates="client")
    notification_logs: Mapped[list[NotificationLog]] = relationship(
        back_populates="client"
    )
    referral_code: Mapped[ReferralCode | None] = relationship(
        back_populates="client",
        cascade="all, delete-orphan",
    )
    sent_referrals: Mapped[list[Referral]] = relationship(
        back_populates="referrer",
        foreign_keys="Referral.referrer_client_id",
    )
    received_referral: Mapped[Referral | None] = relationship(
        back_populates="referred",
        foreign_keys="Referral.referred_client_id",
    )
    referral_bonuses: Mapped[list[ReferralBonus]] = relationship(
        back_populates="client",
        cascade="all, delete-orphan",
    )
    referral_manual_credits: Mapped[list[ReferralManualCredit]] = relationship(
        back_populates="client",
        cascade="all, delete-orphan",
    )


class Slot(Base):
    __tablename__ = "slots"
    __table_args__ = (
        UniqueConstraint("starts_at", "place", name="uq_slots_time_place"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    starts_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    ends_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    place: Mapped[str] = mapped_column(String(500), nullable=False)
    is_blocked: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    note: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utc_now, nullable=False
    )

    bookings: Mapped[list[Booking]] = relationship(back_populates="slot")


class Booking(Base):
    __tablename__ = "bookings"

    id: Mapped[int] = mapped_column(primary_key=True)
    client_id: Mapped[int] = mapped_column(ForeignKey("clients.id"), nullable=False)
    slot_id: Mapped[int] = mapped_column(ForeignKey("slots.id"), nullable=False)
    service: Mapped[str] = mapped_column(String(255), nullable=False)
    starts_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    ends_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    duration_minutes: Mapped[int] = mapped_column(Integer, nullable=False)
    place: Mapped[str] = mapped_column(String(500), nullable=False)
    price_amount: Mapped[Decimal] = mapped_column(Numeric(10, 2), nullable=False)
    final_amount: Mapped[Decimal | None] = mapped_column(Numeric(10, 2))
    status: Mapped[BookingStatus] = mapped_column(
        enum_column(BookingStatus, "bookings_status"),
        default=BookingStatus.DRAFT,
        nullable=False,
    )
    notes: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utc_now, nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utc_now, onupdate=utc_now, nullable=False
    )

    client: Mapped[Client] = relationship(back_populates="bookings")
    slot: Mapped[Slot] = relationship(back_populates="bookings")
    status_history: Mapped[list[BookingStatusHistory]] = relationship(
        back_populates="booking", cascade="all, delete-orphan"
    )
    notification_logs: Mapped[list[NotificationLog]] = relationship(
        back_populates="booking"
    )
    reminder_logs: Mapped[list[ReminderLog]] = relationship(back_populates="booking")
    expenses: Mapped[list[BookingExpense]] = relationship(
        back_populates="booking", cascade="all, delete-orphan"
    )


class BookingStatusHistory(Base):
    __tablename__ = "booking_status_history"

    id: Mapped[int] = mapped_column(primary_key=True)
    booking_id: Mapped[int] = mapped_column(ForeignKey("bookings.id"), nullable=False)
    actor: Mapped[str] = mapped_column(String(50), nullable=False)
    old_status: Mapped[BookingStatus | None] = mapped_column(
        enum_column(BookingStatus, "booking_status_history_old_status")
    )
    new_status: Mapped[BookingStatus] = mapped_column(
        enum_column(BookingStatus, "booking_status_history_new_status"), nullable=False
    )
    reason: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utc_now, nullable=False
    )

    booking: Mapped[Booking] = relationship(back_populates="status_history")


class NotificationLog(Base):
    __tablename__ = "notification_logs"

    id: Mapped[int] = mapped_column(primary_key=True)
    booking_id: Mapped[int | None] = mapped_column(ForeignKey("bookings.id"))
    client_id: Mapped[int | None] = mapped_column(ForeignKey("clients.id"))
    kind: Mapped[str] = mapped_column(String(100), nullable=False)
    recipient_telegram_id: Mapped[int | None] = mapped_column(BigInteger)
    status: Mapped[DeliveryStatus] = mapped_column(
        enum_column(DeliveryStatus, "notification_delivery_status"),
        default=DeliveryStatus.PENDING,
        nullable=False,
    )
    error: Mapped[str | None] = mapped_column(Text)
    sent_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utc_now, nullable=False
    )

    booking: Mapped[Booking | None] = relationship(back_populates="notification_logs")
    client: Mapped[Client | None] = relationship(back_populates="notification_logs")


class ReminderLog(Base):
    __tablename__ = "reminder_logs"
    __table_args__ = (
        UniqueConstraint("booking_id", "reminder_kind", name="uq_reminder_once"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    booking_id: Mapped[int] = mapped_column(ForeignKey("bookings.id"), nullable=False)
    reminder_kind: Mapped[str] = mapped_column(String(50), nullable=False)
    scheduled_for: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )
    status: Mapped[DeliveryStatus] = mapped_column(
        enum_column(DeliveryStatus, "reminder_delivery_status"),
        default=DeliveryStatus.PENDING,
        nullable=False,
    )
    error: Mapped[str | None] = mapped_column(Text)
    sent_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utc_now, nullable=False
    )

    booking: Mapped[Booking] = relationship(back_populates="reminder_logs")


class BookingExpense(Base):
    __tablename__ = "booking_expenses"

    id: Mapped[int] = mapped_column(primary_key=True)
    booking_id: Mapped[int] = mapped_column(ForeignKey("bookings.id"), nullable=False)
    category: Mapped[ExpenseCategory] = mapped_column(
        enum_column(ExpenseCategory, "booking_expense_category"), nullable=False
    )
    amount: Mapped[Decimal] = mapped_column(Numeric(10, 2), nullable=False)
    note: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utc_now, nullable=False
    )

    booking: Mapped[Booking] = relationship(back_populates="expenses")


class ReferralCode(Base):
    __tablename__ = "referral_codes"

    id: Mapped[int] = mapped_column(primary_key=True)
    client_id: Mapped[int] = mapped_column(
        ForeignKey("clients.id"), unique=True, nullable=False
    )
    code: Mapped[str] = mapped_column(String(64), unique=True, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utc_now, nullable=False
    )

    client: Mapped[Client] = relationship(back_populates="referral_code")
    referrals: Mapped[list[Referral]] = relationship(back_populates="referral_code")


class Referral(Base):
    __tablename__ = "referrals"
    __table_args__ = (
        UniqueConstraint("referred_client_id", name="uq_referrals_referred_client"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    referrer_client_id: Mapped[int] = mapped_column(
        ForeignKey("clients.id"), nullable=False
    )
    referred_client_id: Mapped[int] = mapped_column(
        ForeignKey("clients.id"), nullable=False
    )
    referral_code_id: Mapped[int] = mapped_column(
        ForeignKey("referral_codes.id"), nullable=False
    )
    qualified_booking_id: Mapped[int | None] = mapped_column(ForeignKey("bookings.id"))
    status: Mapped[ReferralStatus] = mapped_column(
        enum_column(ReferralStatus, "referral_status"),
        default=ReferralStatus.PENDING,
        nullable=False,
    )
    qualified_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utc_now, nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utc_now, onupdate=utc_now, nullable=False
    )

    referrer: Mapped[Client] = relationship(
        back_populates="sent_referrals",
        foreign_keys=[referrer_client_id],
    )
    referred: Mapped[Client] = relationship(
        back_populates="received_referral",
        foreign_keys=[referred_client_id],
    )
    referral_code: Mapped[ReferralCode] = relationship(back_populates="referrals")
    qualified_booking: Mapped[Booking | None] = relationship()


class ReferralBonus(Base):
    __tablename__ = "referral_bonuses"
    __table_args__ = (
        UniqueConstraint(
            "client_id",
            "referral_count",
            name="uq_referral_bonus_client_count",
        ),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    client_id: Mapped[int] = mapped_column(ForeignKey("clients.id"), nullable=False)
    referral_count: Mapped[int] = mapped_column(Integer, nullable=False)
    reward_label: Mapped[str] = mapped_column(String(255), nullable=False)
    status: Mapped[ReferralBonusStatus] = mapped_column(
        enum_column(ReferralBonusStatus, "referral_bonus_status"),
        default=ReferralBonusStatus.PENDING,
        nullable=False,
    )
    notification_sent_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True)
    )
    awarded_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utc_now, nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utc_now, onupdate=utc_now, nullable=False
    )

    client: Mapped[Client] = relationship(back_populates="referral_bonuses")


class ReferralManualCredit(Base):
    __tablename__ = "referral_manual_credits"

    id: Mapped[int] = mapped_column(primary_key=True)
    client_id: Mapped[int] = mapped_column(ForeignKey("clients.id"), nullable=False)
    amount: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    reason: Mapped[str] = mapped_column(String(255), nullable=False)
    dedupe_key: Mapped[str | None] = mapped_column(String(255), unique=True)
    created_by: Mapped[str | None] = mapped_column(String(255))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utc_now, nullable=False
    )

    client: Mapped[Client] = relationship(back_populates="referral_manual_credits")
