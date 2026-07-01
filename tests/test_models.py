from datetime import UTC, datetime, timedelta
from decimal import Decimal
from pathlib import Path

import pytest
from sqlalchemy import create_engine, inspect, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.db import session as db_session
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
    Referral,
    ReferralBonus,
    ReferralCode,
    ReferralManualCredit,
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
    "referral_codes",
    "referrals",
    "referral_bonuses",
    "referral_manual_credits",
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
        referral_code = ReferralCode(client=client, code="test-code")
        referred_client = Client(
            user=User(telegram_id=456, username="friend"),
            display_name="Friend",
        )
        referral = Referral(
            referrer=client,
            referred=referred_client,
            referral_code=referral_code,
        )
        client.referral_bonuses.append(
            ReferralBonus(
                referral_count=3,
                reward_label="test reward",
            )
        )
        client.referral_manual_credits.append(
            ReferralManualCredit(
                amount=1,
                reason="synthetic test credit",
                dedupe_key="synthetic-credit",
            )
        )

        session.add(booking)
        session.add(referral)
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
    assert saved_booking.client.referral_code is not None
    assert len(saved_booking.client.sent_referrals) == 1
    assert len(saved_booking.client.referral_bonuses) == 1
    assert len(saved_booking.client.referral_manual_credits) == 1


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


def test_booking_requires_slot() -> None:
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    starts_at = datetime(2026, 6, 24, 10, 0, tzinfo=UTC)

    with Session(engine) as session:
        client = Client(user=User(telegram_id=777), display_name="No Slot")
        booking = Booking(
            client=client,
            service="haircut",
            starts_at=starts_at,
            ends_at=starts_at + timedelta(hours=1),
            duration_minutes=60,
            place="Test studio",
            price_amount=Decimal("90.00"),
            status=BookingStatus.CONFIRMED,
        )
        session.add(booking)

        with pytest.raises(IntegrityError):
            session.flush()


@pytest.mark.asyncio
async def test_async_session_helpers_commit_and_rollback() -> None:
    engine = db_session.create_database_engine("sqlite+aiosqlite:///:memory:")
    await db_session.create_all(engine)
    session_factory = db_session.create_session_factory(engine)

    async with db_session.session_scope(session_factory) as session:
        session.add(User(telegram_id=321, display_name="Committed User"))

    async with session_factory() as session:
        committed_user = await session.scalar(
            select(User).where(User.telegram_id == 321)
        )
    assert committed_user is not None

    with pytest.raises(RuntimeError):
        async with db_session.session_scope(session_factory) as session:
            session.add(User(telegram_id=654, display_name="Rolled Back User"))
            raise RuntimeError("force rollback")

    async with session_factory() as session:
        rolled_back_user = await session.scalar(
            select(User).where(User.telegram_id == 654)
        )
    assert rolled_back_user is None

    await db_session.drop_all(engine)
    async with engine.begin() as connection:
        table_names = await connection.run_sync(
            lambda sync_connection: inspect(sync_connection).get_table_names()
        )
    assert table_names == []
    await engine.dispose()
