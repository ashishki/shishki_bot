from datetime import UTC, datetime, timedelta
from decimal import Decimal
from pathlib import Path

from sqlalchemy import create_engine, inspect, select
from sqlalchemy.orm import Session

from app.db.models import (
    Base,
    Booking,
    BookingExpense,
    BookingStatus,
    BookingStatusHistory,
    Client,
    DeliveryStatus,
    ExpenseCategory,
    NotificationLog,
    ReminderLog,
    Slot,
    User,
)

EXPECTED_TABLES = {
    "users",
    "clients",
    "slots",
    "bookings",
    "booking_status_history",
    "notification_logs",
    "reminder_logs",
    "booking_expenses",
}


def test_models_create_minimal_booking_graph() -> None:
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)

    starts_at = datetime(2026, 6, 24, 10, 0, tzinfo=UTC)
    ends_at = starts_at + timedelta(hours=1)
    scheduled_for = starts_at - timedelta(hours=24)

    with Session(engine, expire_on_commit=False) as session:
        user = User(
            telegram_id=123,
            username="test_user",
            display_name="Test User",
        )
        client = Client(user=user, display_name="Test User")
        slot = Slot(starts_at=starts_at, ends_at=ends_at, place="Test studio")
        booking = Booking(
            client=client,
            slot=slot,
            service="haircut",
            starts_at=starts_at,
            ends_at=ends_at,
            duration_minutes=60,
            place="Test studio",
            price_amount=Decimal("90.00"),
            status=BookingStatus.CONFIRMED,
        )
        booking.status_history.append(
            BookingStatusHistory(
                actor="client",
                old_status=BookingStatus.DRAFT,
                new_status=BookingStatus.CONFIRMED,
                reason="initial booking",
            )
        )
        booking.notification_logs.append(
            NotificationLog(
                client=client,
                kind="booking_confirmation",
                recipient_telegram_id=123,
                status=DeliveryStatus.SENT,
                sent_at=starts_at,
            )
        )
        booking.reminder_logs.append(
            ReminderLog(
                reminder_kind="24h",
                scheduled_for=scheduled_for,
                status=DeliveryStatus.PENDING,
            )
        )
        booking.expenses.append(
            BookingExpense(
                category=ExpenseCategory.MATERIALS,
                amount=Decimal("12.50"),
                note="synthetic test expense",
            )
        )

        session.add(booking)
        session.commit()

        saved_booking = session.scalar(select(Booking))

    assert saved_booking is not None
    assert saved_booking.status is BookingStatus.CONFIRMED
    assert saved_booking.client.user is not None
    assert saved_booking.slot is not None
    assert len(saved_booking.status_history) == 1
    assert len(saved_booking.notification_logs) == 1
    assert len(saved_booking.reminder_logs) == 1
    assert len(saved_booking.expenses) == 1


def test_booking_status_enum_matches_architecture() -> None:
    architecture = Path("docs/ARCHITECTURE.md").read_text(encoding="utf-8")
    status_section = architecture.split("## Booking Statuses", maxsplit=1)[1].split(
        "Every status change", maxsplit=1
    )[0]
    expected_statuses = {
        line.removeprefix("- `").removesuffix("`")
        for line in status_section.splitlines()
        if line.startswith("- `")
    }

    assert {status.value for status in BookingStatus} == expected_statuses


def test_metadata_create_all() -> None:
    engine = create_engine("sqlite:///:memory:")

    Base.metadata.create_all(engine)
    inspector = inspect(engine)
    assert set(inspector.get_table_names()) == EXPECTED_TABLES

    Base.metadata.drop_all(engine)
    inspector = inspect(engine)
    assert inspector.get_table_names() == []
