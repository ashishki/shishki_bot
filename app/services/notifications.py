"""Notification delivery service with durable delivery logs."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Protocol

from sqlalchemy.orm import Session

from app.db.models import Booking, Client, DeliveryStatus, NotificationLog


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
    return send_client_message(
        session,
        sender=sender,
        client=booking.client,
        kind=kind,
        text=text,
        booking=booking,
    )


def send_client_message(
    session: Session,
    *,
    sender: NotificationSender,
    client: Client,
    kind: str,
    text: str,
    booking: Booking | None = None,
) -> NotificationLog:
    recipient_telegram_id = _client_telegram_id(client)
    log = NotificationLog(
        booking=booking,
        client=client,
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


def _client_telegram_id(client: Client | None) -> int | None:
    user = client.user if client else None
    return user.telegram_id if user else None
