"""Reminder scheduling and duplicate-send prevention."""

from __future__ import annotations

import inspect
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta

from sqlalchemy import select, update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.db.models import Booking, BookingStatus, DeliveryStatus, ReminderLog
from app.services.notifications import NotificationSender

REMINDER_24H = "24h"
REMINDER_3H = "3h"
REMINDER_OFFSETS = {
    REMINDER_24H: timedelta(hours=24),
    REMINDER_3H: timedelta(hours=3),
}
ACTIVE_REMINDER_BOOKING_STATUSES = (
    BookingStatus.CONFIRMED,
    BookingStatus.RESCHEDULED,
)
RECOVERABLE_REMINDER_STATUSES = (
    DeliveryStatus.PENDING,
    DeliveryStatus.FAILED,
)


@dataclass(frozen=True, slots=True)
class ReminderSchedule:
    reminder_kind: str
    scheduled_for: datetime


def calculate_reminder_times(booking: Booking) -> tuple[ReminderSchedule, ...]:
    starts_at = _as_utc(booking.starts_at)
    return tuple(
        ReminderSchedule(
            reminder_kind=kind,
            scheduled_for=starts_at - offset,
        )
        for kind, offset in REMINDER_OFFSETS.items()
    )


def rebuild_reminder_logs(
    session: Session,
    *,
    now: datetime | None = None,
) -> list[ReminderLog]:
    cutoff = now or datetime.now(UTC)
    logs: list[ReminderLog] = []

    for booking in session.scalars(
        select(Booking)
        .where(
            Booking.status.in_(ACTIVE_REMINDER_BOOKING_STATUSES),
            Booking.starts_at > cutoff,
        )
        .order_by(Booking.starts_at)
    ):
        for schedule in calculate_reminder_times(booking):
            log = ensure_reminder_log(session, booking=booking, schedule=schedule)
            if log.status in RECOVERABLE_REMINDER_STATUSES:
                logs.append(log)

    session.flush()
    return sorted(logs, key=lambda log: (log.scheduled_for, log.id or 0))


def recover_pending_reminders(
    session: Session,
    *,
    now: datetime | None = None,
) -> list[ReminderLog]:
    cutoff = now or datetime.now(UTC)
    return [
        log
        for log in rebuild_reminder_logs(session, now=cutoff)
        if log.scheduled_for <= cutoff and log.status in RECOVERABLE_REMINDER_STATUSES
    ]


def ensure_reminder_log(
    session: Session,
    *,
    booking: Booking,
    schedule: ReminderSchedule,
) -> ReminderLog:
    if booking.id is None:
        raise ValueError("booking must be flushed before reminders can be created")

    existing = session.scalar(
        select(ReminderLog).where(
            ReminderLog.booking_id == booking.id,
            ReminderLog.reminder_kind == schedule.reminder_kind,
        )
    )
    if existing is not None:
        return _reconcile_existing_log(session, existing, schedule)

    log = ReminderLog(
        booking_id=booking.id,
        reminder_kind=schedule.reminder_kind,
        scheduled_for=schedule.scheduled_for,
        status=DeliveryStatus.PENDING,
    )
    try:
        with session.begin_nested():
            session.add(log)
            session.flush()
    except IntegrityError as exc:
        existing = session.scalar(
            select(ReminderLog).where(
                ReminderLog.booking_id == booking.id,
                ReminderLog.reminder_kind == schedule.reminder_kind,
            )
        )
        if existing is None:
            raise exc
        return _reconcile_existing_log(session, existing, schedule)
    return log


def send_due_reminder(
    session: Session,
    *,
    sender: NotificationSender,
    reminder_log: ReminderLog,
    text: str,
) -> ReminderLog:
    if not _claim_reminder_for_delivery(session, reminder_log):
        return reminder_log

    if reminder_log.booking.status not in ACTIVE_REMINDER_BOOKING_STATUSES:
        reminder_log.status = DeliveryStatus.SKIPPED
        reminder_log.error = "Booking is no longer active"
        session.flush()
        return reminder_log

    recipient_telegram_id = _recipient_telegram_id(reminder_log.booking)
    if recipient_telegram_id is None:
        reminder_log.status = DeliveryStatus.FAILED
        reminder_log.error = "Client has no Telegram identity"
        session.flush()
        return reminder_log

    try:
        result = sender.send_message(recipient_telegram_id, text)
        if inspect.isawaitable(result):
            if inspect.iscoroutine(result):
                result.close()
            raise TypeError("NotificationSender.send_message must be synchronous")
    except Exception as exc:  # noqa: BLE001 - delivery failures must be logged
        reminder_log.status = DeliveryStatus.FAILED
        reminder_log.error = str(exc) or exc.__class__.__name__
    else:
        reminder_log.status = DeliveryStatus.SENT
        reminder_log.error = None
        reminder_log.sent_at = datetime.now(UTC)

    session.flush()
    return reminder_log


def _claim_reminder_for_delivery(session: Session, reminder_log: ReminderLog) -> bool:
    if reminder_log.id is None:
        raise ValueError("reminder_log must be flushed before it can be sent")

    claim = session.execute(
        update(ReminderLog)
        .where(
            ReminderLog.id == reminder_log.id,
            ReminderLog.status.in_(RECOVERABLE_REMINDER_STATUSES),
        )
        .values(status=DeliveryStatus.PROCESSING, error=None)
        .execution_options(synchronize_session=False)
    )
    if claim.rowcount != 1:
        session.refresh(reminder_log)
        return False

    session.refresh(reminder_log)
    return True


def _reconcile_existing_log(
    session: Session,
    log: ReminderLog,
    schedule: ReminderSchedule,
) -> ReminderLog:
    if _as_utc(log.scheduled_for) != _as_utc(schedule.scheduled_for):
        log.scheduled_for = schedule.scheduled_for
        log.status = DeliveryStatus.PENDING
        log.error = None
        log.sent_at = None
        session.flush()
    return log


def _recipient_telegram_id(booking: Booking) -> int | None:
    user = booking.client.user if booking and booking.client else None
    return user.telegram_id if user else None


def _as_utc(value: datetime) -> datetime:
    if value.tzinfo is None:
        return value.replace(tzinfo=UTC)
    return value.astimezone(UTC)
