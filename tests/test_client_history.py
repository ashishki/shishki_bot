from datetime import UTC, datetime, timedelta
from decimal import Decimal

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from app.bot.handlers.admin import AdminAccessDenied, handle_admin_client_card
from app.config import Settings
from app.db.models import Base, Booking, BookingStatus, Client, Slot, User
from app.services.clients import ClientServiceError, client_card_summary


def test_client_card_summary() -> None:
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)

    with Session(engine, expire_on_commit=False) as session:
        client = _create_client(
            session,
            display_name="Test Client",
            username="test_client",
            notes="Prefers mornings",
        )
        first_visit = _create_booking(
            session,
            client=client,
            starts_at=datetime(2026, 6, 20, 10, 0, tzinfo=UTC),
            service="haircut",
            final_amount=Decimal("90.00"),
            status=BookingStatus.COMPLETED,
        )
        second_visit = _create_booking(
            session,
            client=client,
            starts_at=datetime(2026, 6, 23, 11, 0, tzinfo=UTC),
            service="coloring",
            final_amount=Decimal("250.00"),
            status=BookingStatus.COMPLETED,
        )
        _create_booking(
            session,
            client=client,
            starts_at=datetime(2026, 6, 24, 11, 0, tzinfo=UTC),
            service="haircut",
            final_amount=Decimal("999.00"),
            status=BookingStatus.CANCELLED_BY_CLIENT,
        )
        session.commit()

        card = client_card_summary(session, client_id=client.id)

    assert card.client_id == client.id
    assert card.display_name == "Test Client"
    assert card.username == "test_client"
    assert card.notes == "Prefers mornings"
    assert card.visit_count == 2
    assert card.total_spent == Decimal("340.00")
    assert card.last_visit == datetime(2026, 6, 23, 11, 0, tzinfo=UTC)
    assert card.services_summary == {"haircut": 1, "coloring": 1}
    assert tuple(visit.booking_id for visit in card.visits) == (
        first_visit.id,
        second_visit.id,
    )


def test_client_total_spent() -> None:
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)

    with Session(engine, expire_on_commit=False) as session:
        client = _create_client(session, display_name=None, username="history_client")
        _create_booking(
            session,
            client=client,
            starts_at=datetime(2026, 6, 20, 10, 0, tzinfo=UTC),
            service="haircut",
            final_amount=Decimal("90.00"),
            status=BookingStatus.COMPLETED,
        )
        _create_booking(
            session,
            client=client,
            starts_at=datetime(2026, 6, 21, 10, 0, tzinfo=UTC),
            service="manual complex service",
            final_amount=Decimal("180.00"),
            status=BookingStatus.COMPLETED,
        )
        _create_booking(
            session,
            client=client,
            starts_at=datetime(2026, 6, 22, 10, 0, tzinfo=UTC),
            service="confirmed only",
            final_amount=Decimal("300.00"),
            status=BookingStatus.CONFIRMED,
        )
        _create_booking(
            session,
            client=client,
            starts_at=datetime(2026, 6, 23, 10, 0, tzinfo=UTC),
            service="no show",
            final_amount=Decimal("400.00"),
            status=BookingStatus.NO_SHOW,
        )
        _create_booking(
            session,
            client=client,
            starts_at=datetime(2026, 6, 24, 10, 0, tzinfo=UTC),
            service="missing final amount",
            final_amount=None,
            status=BookingStatus.COMPLETED,
        )

        other_client = _create_client(
            session,
            telegram_id=456,
            username="other_client",
        )
        _create_booking(
            session,
            client=other_client,
            starts_at=datetime(2026, 6, 25, 10, 0, tzinfo=UTC),
            service="haircut",
            final_amount=Decimal("999.00"),
            status=BookingStatus.COMPLETED,
        )
        session.commit()

        card = client_card_summary(session, client_id=client.id)

    assert card.display_name == "@history_client"
    assert card.visit_count == 2
    assert card.total_spent == Decimal("270.00")
    assert card.services_summary == {"haircut": 1, "manual complex service": 1}


def test_admin_client_card_requires_allowlist() -> None:
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    settings = _settings()

    with Session(engine, expire_on_commit=False) as session:
        client = _create_client(session)
        _create_booking(
            session,
            client=client,
            starts_at=datetime(2026, 6, 20, 10, 0, tzinfo=UTC),
            service="haircut",
            final_amount=Decimal("90.00"),
            status=BookingStatus.COMPLETED,
        )

        with pytest.raises(AdminAccessDenied):
            handle_admin_client_card(
                session,
                settings,
                telegram_user_id=222,
                client_id=client.id,
            )

        response = handle_admin_client_card(
            session,
            settings,
            telegram_user_id=111,
            client_id=client.id,
        )

    assert response.client_card.total_spent == Decimal("90.00")


def test_client_card_missing_client() -> None:
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)

    with Session(engine) as session, pytest.raises(ClientServiceError):
        client_card_summary(session, client_id=999)


def _settings() -> Settings:
    return Settings(
        bot_token="test-token",
        admin_telegram_ids=(111,),
        database_url="sqlite+aiosqlite:///:memory:",
        timezone="Asia/Tbilisi",
        default_place="Test studio",
        stylist_contact_url="https://t.me/test_stylist",
        env="test",
    )


def _create_client(
    session: Session,
    *,
    telegram_id: int = 123,
    display_name: str | None = "Test Client",
    username: str | None = "test_client",
    notes: str | None = None,
) -> Client:
    client = Client(
        user=User(
            telegram_id=telegram_id,
            username=username,
            display_name=display_name,
        ),
        display_name=display_name,
        notes=notes,
    )
    session.add(client)
    session.flush()
    return client


def _create_booking(
    session: Session,
    *,
    client: Client,
    starts_at: datetime,
    service: str,
    final_amount: Decimal | None,
    status: BookingStatus,
) -> Booking:
    slot = Slot(
        starts_at=starts_at,
        ends_at=starts_at + timedelta(hours=1),
        place="Test studio",
    )
    booking = Booking(
        client=client,
        slot=slot,
        service=service,
        starts_at=starts_at,
        ends_at=starts_at + timedelta(hours=1),
        duration_minutes=60,
        place="Test studio",
        price_amount=Decimal("90.00"),
        final_amount=final_amount,
        status=status,
    )
    session.add(booking)
    session.flush()
    return booking
