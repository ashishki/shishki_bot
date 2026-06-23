"""Deterministic booking creation and slot availability rules.

The service participates in a caller-owned SQLAlchemy transaction: it locks the
slot, adds the booking, and flushes. Callers must commit or roll back the
session boundary that includes booking creation and any immediate follow-up
work.
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.db.models import Booking, BookingStatus, BookingStatusHistory, Client, Slot

HAIRCUT_SERVICE = "haircut"
DEFAULT_HAIRCUT_DURATION_MINUTES = 60
DEFAULT_HAIRCUT_PRICE = Decimal("90.00")


class BookingServiceError(ValueError):
    """Base error for deterministic booking failures."""


class SlotUnavailableError(BookingServiceError):
    """Raised when a slot cannot be booked."""


class UnsupportedSelfBookServiceError(BookingServiceError):
    """Raised when clients try to self-book a complex service."""


def create_haircut_booking(
    session: Session,
    *,
    client_id: int,
    slot_id: int,
) -> Booking:
    return create_simple_booking(
        session,
        client_id=client_id,
        slot_id=slot_id,
        service=HAIRCUT_SERVICE,
    )


def create_simple_booking(
    session: Session,
    *,
    client_id: int,
    slot_id: int,
    service: str,
) -> Booking:
    normalized_service = service.strip().lower()
    if normalized_service != HAIRCUT_SERVICE:
        raise UnsupportedSelfBookServiceError(
            "Only simple haircut bookings can be self-booked"
        )

    client = session.get(Client, client_id)
    if client is None:
        raise BookingServiceError(f"Client not found: {client_id}")

    slot = _lock_available_slot(session, slot_id)
    starts_at = _as_utc(slot.starts_at)
    ends_at = starts_at + timedelta(minutes=DEFAULT_HAIRCUT_DURATION_MINUTES)

    booking: Booking | None = None
    try:
        with session.begin_nested():
            booking = Booking(
                client=client,
                slot=slot,
                service=HAIRCUT_SERVICE,
                starts_at=starts_at,
                ends_at=ends_at,
                duration_minutes=DEFAULT_HAIRCUT_DURATION_MINUTES,
                place=slot.place,
                price_amount=DEFAULT_HAIRCUT_PRICE,
                status=BookingStatus.CONFIRMED,
            )
            booking.status_history.append(
                BookingStatusHistory(
                    actor="client",
                    old_status=BookingStatus.DRAFT,
                    new_status=BookingStatus.CONFIRMED,
                    reason="self-booked haircut",
                )
            )
            session.add(booking)
            session.flush()
    except IntegrityError as exc:
        raise SlotUnavailableError(f"Slot is already booked: {slot_id}") from exc

    if booking is None:
        raise SlotUnavailableError(f"Slot is already booked: {slot_id}")
    return booking


def list_available_slots(
    session: Session,
    *,
    now: datetime | None = None,
) -> list[Slot]:
    cutoff = now or datetime.now(UTC)
    statement = (
        select(Slot)
        .outerjoin(Booking)
        .where(
            Slot.is_blocked.is_(False),
            Slot.starts_at > cutoff,
            Booking.id.is_(None),
        )
        .order_by(Slot.starts_at)
    )
    return list(session.scalars(statement))


def _lock_available_slot(session: Session, slot_id: int) -> Slot:
    statement = select(Slot).where(Slot.id == slot_id).with_for_update()
    slot = session.scalars(statement).one_or_none()
    if slot is None or slot.is_blocked or _as_utc(slot.starts_at) <= datetime.now(UTC):
        raise SlotUnavailableError(f"Slot is unavailable: {slot_id}")

    existing_booking = session.scalar(
        select(Booking.id).where(Booking.slot_id == slot.id)
    )
    if existing_booking is not None:
        raise SlotUnavailableError(f"Slot is already booked: {slot_id}")

    return slot


def _as_utc(value: datetime) -> datetime:
    if value.tzinfo is None:
        return value.replace(tzinfo=UTC)
    return value.astimezone(UTC)
