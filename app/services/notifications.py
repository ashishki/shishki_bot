"""Notification delivery service with durable delivery logs."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Protocol

from sqlalchemy.orm import Session

from app.db.models import Booking, DeliveryStatus, NotificationLog


class NotificationSender(Protocol):
    def send_message(self, recipient_telegram_id: int, text: str) -> None:
        """Send one message or raise an exception on delivery failure."""


def send_client_notification(
    session: Session,
    *,
    sender: NotificationSender,
    booking: Booking,
    kind: str,
    text: str,
) -> NotificationLog:
    recipient_telegram_id = _recipient_telegram_id(booking)
    log = NotificationLog(
        booking=booking,
        client=booking.client,
        kind=kind,
        recipient_telegram_id=recipient_telegram_id,
        status=DeliveryStatus.PENDING,
    )
    session.add(log)

    if recipient_telegram_id is None:
        log.status = DeliveryStatus.FAILED
        log.error = "Client has no Telegram identity"
        session.flush()
        return log

    try:
        sender.send_message(recipient_telegram_id, text)
    except Exception as exc:  # noqa: BLE001 - delivery failures must be logged
        log.status = DeliveryStatus.FAILED
        log.error = str(exc) or exc.__class__.__name__
    else:
        log.status = DeliveryStatus.SENT
        log.sent_at = datetime.now(UTC)

    session.flush()
    return log


def _recipient_telegram_id(booking: Booking) -> int | None:
    user = booking.client.user if booking.client else None
    return user.telegram_id if user else None
