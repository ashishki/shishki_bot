"""Client history and spending summaries for admin views."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.models import Booking, BookingStatus, Client
from app.services.finance import ZERO_MONEY


class ClientServiceError(ValueError):
    """Raised when deterministic client summary rules reject a request."""


@dataclass(frozen=True, slots=True)
class ClientVisit:
    booking_id: int
    service: str
    starts_at: datetime
    final_amount: Decimal


@dataclass(frozen=True, slots=True)
class ClientCard:
    client_id: int
    display_name: str
    username: str | None
    notes: str | None
    visit_count: int
    total_spent: Decimal
    last_visit: datetime | None
    services_summary: dict[str, int]
    visits: tuple[ClientVisit, ...]


def client_card_summary(session: Session, *, client_id: int) -> ClientCard:
    client = session.get(Client, client_id)
    if client is None:
        raise ClientServiceError(f"Client not found: {client_id}")

    completed_bookings = sorted(
        (
            booking
            for booking in session.scalars(
                select(Booking).where(
                    Booking.client_id == client.id,
                    Booking.status == BookingStatus.COMPLETED,
                    Booking.final_amount.is_not(None),
                )
            )
        ),
        key=lambda booking: _as_utc(booking.starts_at),
    )

    visits = tuple(
        ClientVisit(
            booking_id=booking.id,
            service=booking.service,
            starts_at=_as_utc(booking.starts_at),
            final_amount=booking.final_amount or ZERO_MONEY,
        )
        for booking in completed_bookings
    )
    services_summary: dict[str, int] = {}
    for visit in visits:
        services_summary[visit.service] = services_summary.get(visit.service, 0) + 1

    return ClientCard(
        client_id=client.id,
        display_name=_display_name(client),
        username=client.user.username if client.user else None,
        notes=client.notes,
        visit_count=len(visits),
        total_spent=sum((visit.final_amount for visit in visits), ZERO_MONEY),
        last_visit=visits[-1].starts_at if visits else None,
        services_summary=services_summary,
        visits=visits,
    )


def _display_name(client: Client) -> str:
    if client.display_name:
        return client.display_name
    if client.user and client.user.display_name:
        return client.user.display_name
    if client.user and client.user.username:
        return f"@{client.user.username}"
    return f"Client #{client.id}"


def _as_utc(value: datetime) -> datetime:
    if value.tzinfo is None:
        return value.replace(tzinfo=UTC)
    return value.astimezone(UTC)
