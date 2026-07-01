"""Deterministic booking creation and slot availability rules.

The service participates in a caller-owned SQLAlchemy transaction: it locks the
slot, adds the booking, and flushes. Callers must commit or roll back the
session boundary that includes booking creation and any immediate follow-up
work.
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from decimal import Decimal
from zoneinfo import ZoneInfo

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.db.models import Booking, BookingStatus, BookingStatusHistory, Client, Slot

HAIRCUT_SERVICE = "haircut"
HAIRCUT_MALE_SERVICE = "haircut_male"
HAIRCUT_FEMALE_SERVICE = "haircut_female"
DEFAULT_HAIRCUT_SERVICE = HAIRCUT_MALE_SERVICE
HAIRCUT_SERVICES = (
    HAIRCUT_SERVICE,
    HAIRCUT_MALE_SERVICE,
    HAIRCUT_FEMALE_SERVICE,
)
DEFAULT_HAIRCUT_DURATION_MINUTES = 60
MALE_HAIRCUT_PRICE = Decimal("100.00")
FEMALE_HAIRCUT_PRICE = Decimal("120.00")
DEFAULT_HAIRCUT_PRICE = MALE_HAIRCUT_PRICE
HAIRCUT_PRICE_BY_SERVICE = {
    HAIRCUT_SERVICE: MALE_HAIRCUT_PRICE,
    HAIRCUT_MALE_SERVICE: MALE_HAIRCUT_PRICE,
    HAIRCUT_FEMALE_SERVICE: FEMALE_HAIRCUT_PRICE,
}
HAIRCUT_LABEL_BY_SERVICE = {
    HAIRCUT_SERVICE: "Стрижка",
    HAIRCUT_MALE_SERVICE: "Мужская стрижка",
    HAIRCUT_FEMALE_SERVICE: "Женская стрижка",
}
ACTIVE_BOOKING_STATUSES = (
    BookingStatus.DRAFT,
    BookingStatus.CONFIRMED,
    BookingStatus.RESCHEDULED,
)
DEFAULT_BOOKING_TIMEZONE = ZoneInfo("Asia/Tbilisi")


class BookingServiceError(ValueError):
    """Base error for deterministic booking failures."""


class SlotUnavailableError(BookingServiceError):
    """Raised when a slot cannot be booked."""


class UnsupportedSelfBookServiceError(BookingServiceError):
    """Raised when clients try to self-book a complex service."""


def create_manual_booking(
    session: Session,
    *,
    client_id: int,
    slot_id: int,
    service: str,
    duration_minutes: int,
    price_amount: Decimal,
    place: str | None = None,
    notes: str | None = None,
) -> Booking:
    service = _required_text(service, "service")
    _validate_duration(duration_minutes)
    price_amount = _validate_price(price_amount)
    manual_place = _required_text(place, "place") if place is not None else None

    client = session.get(Client, client_id)
    if client is None:
        raise BookingServiceError(f"Client not found: {client_id}")

    slot = _lock_available_slot(session, slot_id)
    starts_at = _booking_time_from_slot(slot.starts_at)
    ends_at = starts_at + timedelta(minutes=duration_minutes)
    _ensure_no_active_booking_overlap(session, starts_at=starts_at, ends_at=ends_at)

    booking: Booking | None = None
    try:
        with session.begin_nested():
            booking = Booking(
                client=client,
                slot=slot,
                service=service,
                starts_at=starts_at,
                ends_at=ends_at,
                duration_minutes=duration_minutes,
                place=manual_place or slot.place,
                price_amount=price_amount,
                status=BookingStatus.CONFIRMED,
                notes=notes,
            )
            booking.status_history.append(
                BookingStatusHistory(
                    actor="admin",
                    old_status=BookingStatus.DRAFT,
                    new_status=BookingStatus.CONFIRMED,
                    reason="manual booking",
                )
            )
            session.add(booking)
            session.flush()
    except IntegrityError as exc:
        raise SlotUnavailableError(f"Slot is already booked: {slot_id}") from exc

    if booking is None:
        raise SlotUnavailableError(f"Slot is already booked: {slot_id}")
    return booking


def create_haircut_booking(
    session: Session,
    *,
    client_id: int,
    slot_id: int,
    service: str = DEFAULT_HAIRCUT_SERVICE,
) -> Booking:
    return create_simple_booking(
        session,
        client_id=client_id,
        slot_id=slot_id,
        service=service,
    )


def create_simple_booking(
    session: Session,
    *,
    client_id: int,
    slot_id: int,
    service: str,
) -> Booking:
    try:
        normalized_service = normalize_haircut_service(service)
    except BookingServiceError as exc:
        raise UnsupportedSelfBookServiceError(
            "Only simple haircut bookings can be self-booked"
        ) from exc

    client = session.get(Client, client_id)
    if client is None:
        raise BookingServiceError(f"Client not found: {client_id}")

    slot = _lock_available_slot(session, slot_id)
    starts_at = _booking_time_from_slot(slot.starts_at)
    ends_at = starts_at + timedelta(minutes=DEFAULT_HAIRCUT_DURATION_MINUTES)
    _ensure_no_active_booking_overlap(session, starts_at=starts_at, ends_at=ends_at)

    booking: Booking | None = None
    try:
        with session.begin_nested():
            booking = Booking(
                client=client,
                slot=slot,
                service=normalized_service,
                starts_at=starts_at,
                ends_at=ends_at,
                duration_minutes=DEFAULT_HAIRCUT_DURATION_MINUTES,
                place=slot.place,
                price_amount=haircut_price_for_service(normalized_service),
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


def normalize_haircut_service(service: str) -> str:
    normalized_service = service.strip().lower()
    if normalized_service == HAIRCUT_SERVICE:
        return DEFAULT_HAIRCUT_SERVICE
    if normalized_service in (HAIRCUT_MALE_SERVICE, HAIRCUT_FEMALE_SERVICE):
        return normalized_service
    raise BookingServiceError(f"Unsupported haircut service: {service}")


def is_haircut_service(service: str) -> bool:
    return service.strip().lower() in HAIRCUT_SERVICES


def haircut_price_for_service(service: str) -> Decimal:
    normalized_service = normalize_haircut_service(service)
    return HAIRCUT_PRICE_BY_SERVICE[normalized_service]


def haircut_service_label(service: str) -> str:
    normalized_service = service.strip().lower()
    return HAIRCUT_LABEL_BY_SERVICE.get(normalized_service, service)


def reschedule_booking(
    session: Session,
    *,
    booking_id: int,
    new_slot_id: int,
    reason: str | None = None,
) -> Booking:
    return _reschedule_booking(
        session,
        booking_id=booking_id,
        new_slot_id=new_slot_id,
        actor="admin",
        reason=reason or "admin rescheduled booking",
    )


def reschedule_booking_by_client(
    session: Session,
    *,
    booking_id: int,
    new_slot_id: int,
    reason: str | None = None,
) -> Booking:
    return _reschedule_booking(
        session,
        booking_id=booking_id,
        new_slot_id=new_slot_id,
        actor="client",
        reason=reason or "client rescheduled booking",
    )


def _reschedule_booking(
    session: Session,
    *,
    booking_id: int,
    new_slot_id: int,
    actor: str,
    reason: str,
) -> Booking:
    booking = _get_booking(session, booking_id)
    new_slot = _lock_available_slot(session, new_slot_id)
    old_status = booking.status
    starts_at = _booking_time_from_slot(new_slot.starts_at)

    try:
        with session.begin_nested():
            booking.slot = new_slot
            booking.starts_at = starts_at
            booking.ends_at = starts_at + timedelta(minutes=booking.duration_minutes)
            booking.place = new_slot.place
            booking.status = BookingStatus.RESCHEDULED
            booking.status_history.append(
                BookingStatusHistory(
                    actor=actor,
                    old_status=old_status,
                    new_status=BookingStatus.RESCHEDULED,
                    reason=reason,
                )
            )
            session.flush()
    except IntegrityError as exc:
        raise SlotUnavailableError(f"Slot is already booked: {new_slot_id}") from exc

    return booking


def cancel_booking_by_admin(
    session: Session,
    *,
    booking_id: int,
    reason: str | None = None,
) -> Booking:
    booking = _get_booking(session, booking_id)
    old_status = booking.status

    with session.begin_nested():
        booking.status = BookingStatus.CANCELLED_BY_ADMIN
        booking.status_history.append(
            BookingStatusHistory(
                actor="admin",
                old_status=old_status,
                new_status=BookingStatus.CANCELLED_BY_ADMIN,
                reason=reason or "admin cancelled booking",
            )
        )
        session.flush()

    return booking


def cancel_booking_by_client(
    session: Session,
    *,
    booking_id: int,
    reason: str | None = None,
) -> Booking:
    booking = _get_booking(session, booking_id)
    old_status = booking.status

    with session.begin_nested():
        booking.status = BookingStatus.CANCELLED_BY_CLIENT
        booking.status_history.append(
            BookingStatusHistory(
                actor="client",
                old_status=old_status,
                new_status=BookingStatus.CANCELLED_BY_CLIENT,
                reason=reason or "client cancelled booking",
            )
        )
        session.flush()

    return booking


def update_booking_details_by_admin(
    session: Session,
    *,
    booking_id: int,
    service: str | None = None,
    duration_minutes: int | None = None,
    price_amount: Decimal | None = None,
    place: str | None = None,
    notes: str | None = None,
) -> Booking:
    booking = _get_booking(session, booking_id)
    changes: list[str] = []

    with session.begin_nested():
        if service is not None:
            booking.service = _required_text(service, "service")
            changes.append("service")
        if duration_minutes is not None:
            _validate_duration(duration_minutes)
            booking.duration_minutes = duration_minutes
            booking.ends_at = booking.starts_at + timedelta(minutes=duration_minutes)
            changes.append("duration")
        if price_amount is not None:
            booking.price_amount = _validate_price(price_amount)
            changes.append("price")
        if place is not None:
            booking.place = _required_text(place, "place")
            changes.append("place")
        if notes is not None:
            booking.notes = notes
            changes.append("notes")

        if changes:
            booking.status_history.append(
                BookingStatusHistory(
                    actor="admin",
                    old_status=booking.status,
                    new_status=booking.status,
                    reason=f"admin updated {', '.join(changes)}",
                )
            )
        session.flush()

    return booking


def list_available_slots(
    session: Session,
    *,
    now: datetime | None = None,
) -> list[Slot]:
    cutoff = now or datetime.now(UTC)
    active_overlap = (
        select(Booking.id)
        .where(
            Booking.status.in_(ACTIVE_BOOKING_STATUSES),
            Booking.starts_at < Slot.ends_at,
            Booking.ends_at > Slot.starts_at,
        )
        .exists()
    )
    statement = (
        select(Slot)
        .where(
            Slot.is_blocked.is_(False),
            Slot.starts_at > cutoff,
            ~active_overlap,
        )
        .order_by(Slot.starts_at)
    )
    return list(session.scalars(statement))


def _lock_available_slot(session: Session, slot_id: int) -> Slot:
    statement = select(Slot).where(Slot.id == slot_id).with_for_update()
    slot = session.scalars(statement).one_or_none()
    if slot is None or slot.is_blocked or _as_utc(slot.starts_at) <= datetime.now(UTC):
        raise SlotUnavailableError(f"Slot is unavailable: {slot_id}")

    existing_booking = _active_booking_overlap_id(
        session,
        starts_at=slot.starts_at,
        ends_at=slot.ends_at,
    )
    if existing_booking is not None:
        raise SlotUnavailableError(f"Slot is already booked: {slot_id}")

    return slot


def _ensure_no_active_booking_overlap(
    session: Session,
    *,
    starts_at: datetime,
    ends_at: datetime,
) -> None:
    existing_booking = _active_booking_overlap_id(
        session,
        starts_at=starts_at,
        ends_at=ends_at,
    )
    if existing_booking is not None:
        raise SlotUnavailableError("Booking overlaps an active booking")


def _active_booking_overlap_id(
    session: Session,
    *,
    starts_at: datetime,
    ends_at: datetime,
) -> int | None:
    with session.no_autoflush:
        return session.scalar(
            select(Booking.id).where(
                Booking.status.in_(ACTIVE_BOOKING_STATUSES),
                Booking.starts_at < ends_at,
                Booking.ends_at > starts_at,
            )
        )


def _get_booking(session: Session, booking_id: int) -> Booking:
    booking = session.get(Booking, booking_id)
    if booking is None:
        raise BookingServiceError(f"Booking not found: {booking_id}")
    return booking


def _required_text(value: str, field_name: str) -> str:
    cleaned = value.strip()
    if not cleaned:
        raise BookingServiceError(f"{field_name} is required")
    return cleaned


def _validate_duration(duration_minutes: int) -> None:
    if duration_minutes <= 0:
        raise BookingServiceError("duration_minutes must be positive")


def _validate_price(price_amount: Decimal) -> Decimal:
    if price_amount < 0:
        raise BookingServiceError("price_amount must not be negative")
    return price_amount


def _as_utc(value: datetime) -> datetime:
    if value.tzinfo is None:
        return value.replace(tzinfo=DEFAULT_BOOKING_TIMEZONE).astimezone(UTC)
    return value.astimezone(UTC)


def _booking_time_from_slot(value: datetime) -> datetime:
    if value.tzinfo is None:
        return value
    return value.astimezone(UTC)
