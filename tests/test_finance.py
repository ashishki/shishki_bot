from datetime import UTC, datetime, timedelta
from decimal import Decimal

import pytest
from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session

from app.bot.handlers.admin import (
    AdminAccessDenied,
    handle_admin_complete_booking,
    handle_admin_weekly_revenue,
)
from app.config import Settings
from app.db.models import (
    Base,
    Booking,
    BookingExpense,
    BookingStatus,
    Client,
    ExpenseCategory,
    Slot,
    User,
)
from app.services.finance import (
    ExpenseInput,
    FinanceServiceError,
    add_booking_expense,
    complete_booking,
    weekly_revenue_summary,
)


def test_complete_booking_with_expenses() -> None:
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)

    with Session(engine, expire_on_commit=False) as session:
        booking = _create_booking(
            session,
            starts_at=datetime(2026, 6, 23, 10, 0, tzinfo=UTC),
        )

        completed = complete_booking(
            session,
            booking_id=booking.id,
            final_amount=Decimal("120.00"),
            expenses=(
                ExpenseInput(
                    category=ExpenseCategory.MATERIALS,
                    amount=Decimal("15.50"),
                    note="Synthetic materials",
                ),
                ExpenseInput(
                    category=ExpenseCategory.ASSISTANT,
                    amount=Decimal("20.00"),
                ),
            ),
            reason="appointment finished",
        )
        session.commit()

        saved_expenses = session.scalars(select(BookingExpense)).all()

    assert completed.status is BookingStatus.COMPLETED
    assert completed.final_amount == Decimal("120.00")
    assert len(saved_expenses) == 2
    assert {expense.category for expense in saved_expenses} == {
        ExpenseCategory.MATERIALS,
        ExpenseCategory.ASSISTANT,
    }
    assert completed.status_history[-1].old_status is BookingStatus.CONFIRMED
    assert completed.status_history[-1].new_status is BookingStatus.COMPLETED
    assert completed.status_history[-1].reason == "appointment finished"


def test_weekly_gross_revenue() -> None:
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    week_start = datetime(2026, 6, 22, 0, 0, tzinfo=UTC)

    with Session(engine, expire_on_commit=False) as session:
        _completed_booking(
            session,
            starts_at=week_start + timedelta(days=1),
            final_amount=Decimal("120.00"),
        )
        _completed_booking(
            session,
            starts_at=week_start + timedelta(days=3),
            final_amount=Decimal("180.00"),
        )
        _completed_booking(
            session,
            starts_at=week_start - timedelta(hours=1),
            final_amount=Decimal("999.00"),
        )
        _create_booking(
            session,
            starts_at=week_start + timedelta(days=2),
            final_amount=Decimal("90.00"),
            status=BookingStatus.CANCELLED_BY_CLIENT,
        )
        _create_booking(
            session,
            starts_at=week_start + timedelta(days=4),
            final_amount=Decimal("80.00"),
            status=BookingStatus.NO_SHOW,
        )
        _create_booking(
            session,
            starts_at=week_start + timedelta(days=5),
            final_amount=Decimal("70.00"),
            status=BookingStatus.CONFIRMED,
        )
        session.commit()

        summary = weekly_revenue_summary(session, week_start=week_start)

    assert summary.completed_count == 2
    assert summary.gross_revenue == Decimal("300.00")
    assert summary.total_expenses == Decimal("0.00")
    assert summary.estimated_net == Decimal("300.00")


def test_weekly_net_revenue() -> None:
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    week_start = datetime(2026, 6, 22, 0, 0, tzinfo=UTC)

    with Session(engine, expire_on_commit=False) as session:
        first = _completed_booking(
            session,
            starts_at=week_start + timedelta(days=1),
            final_amount=Decimal("250.00"),
            expenses=(
                ExpenseInput(ExpenseCategory.MATERIALS, Decimal("40.00")),
                ExpenseInput(ExpenseCategory.RENT, Decimal("30.00")),
            ),
        )
        _completed_booking(
            session,
            starts_at=week_start + timedelta(days=2),
            final_amount=Decimal("150.00"),
            expenses=(
                ExpenseInput(ExpenseCategory.ASSISTANT, Decimal("50.00")),
                ExpenseInput(ExpenseCategory.OTHER, Decimal("10.00")),
            ),
        )
        add_booking_expense(
            session,
            booking_id=first.id,
            category=ExpenseCategory.OTHER,
            amount=Decimal("5.00"),
            note="Synthetic extra cost",
        )
        _create_booking(
            session,
            starts_at=week_start + timedelta(days=3),
            final_amount=Decimal("999.00"),
            status=BookingStatus.CANCELLED_BY_ADMIN,
            expenses=(ExpenseInput(ExpenseCategory.MATERIALS, Decimal("999.00")),),
        )
        session.commit()

        summary = weekly_revenue_summary(session, week_start=week_start)

    assert summary.gross_revenue == Decimal("400.00")
    assert summary.expenses_by_category == {
        ExpenseCategory.MATERIALS: Decimal("40.00"),
        ExpenseCategory.RENT: Decimal("30.00"),
        ExpenseCategory.ASSISTANT: Decimal("50.00"),
        ExpenseCategory.OTHER: Decimal("15.00"),
    }
    assert summary.total_expenses == Decimal("135.00")
    assert summary.estimated_net == Decimal("265.00")


def test_finance_rejects_invalid_completion() -> None:
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)

    with Session(engine, expire_on_commit=False) as session:
        cancelled = _create_booking(
            session,
            starts_at=datetime(2026, 6, 23, 10, 0, tzinfo=UTC),
            status=BookingStatus.CANCELLED_BY_ADMIN,
        )
        active = _create_booking(
            session,
            starts_at=datetime(2026, 6, 24, 10, 0, tzinfo=UTC),
        )

        with pytest.raises(FinanceServiceError, match="cannot be completed"):
            complete_booking(
                session,
                booking_id=cancelled.id,
                final_amount=Decimal("100.00"),
            )

        with pytest.raises(FinanceServiceError, match="must not be negative"):
            complete_booking(
                session,
                booking_id=active.id,
                final_amount=Decimal("-1.00"),
            )


def test_admin_finance_handlers_require_allowlist() -> None:
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    settings = _settings()

    with Session(engine, expire_on_commit=False) as session:
        booking = _create_booking(
            session,
            starts_at=datetime(2026, 6, 23, 10, 0, tzinfo=UTC),
        )

        with pytest.raises(AdminAccessDenied):
            handle_admin_complete_booking(
                session,
                settings,
                telegram_user_id=222,
                booking_id=booking.id,
                final_amount=Decimal("120.00"),
            )

        with pytest.raises(AdminAccessDenied):
            handle_admin_weekly_revenue(
                session,
                settings,
                telegram_user_id=222,
                week_start=datetime(2026, 6, 22, 0, 0, tzinfo=UTC),
            )

        response = handle_admin_complete_booking(
            session,
            settings,
            telegram_user_id=111,
            booking_id=booking.id,
            final_amount=Decimal("120.00"),
            expenses=(ExpenseInput(ExpenseCategory.MATERIALS, Decimal("10.00")),),
        )
        revenue = handle_admin_weekly_revenue(
            session,
            settings,
            telegram_user_id=111,
            week_start=datetime(2026, 6, 22, 0, 0, tzinfo=UTC),
        )

    assert response.booking.status is BookingStatus.COMPLETED
    assert revenue.summary.gross_revenue == Decimal("120.00")
    assert revenue.summary.estimated_net == Decimal("110.00")


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


def _completed_booking(
    session: Session,
    *,
    starts_at: datetime,
    final_amount: Decimal,
    expenses: tuple[ExpenseInput, ...] = (),
) -> Booking:
    booking = _create_booking(session, starts_at=starts_at)
    return complete_booking(
        session,
        booking_id=booking.id,
        final_amount=final_amount,
        expenses=expenses,
    )


def _create_booking(
    session: Session,
    *,
    starts_at: datetime,
    final_amount: Decimal | None = None,
    status: BookingStatus = BookingStatus.CONFIRMED,
    expenses: tuple[ExpenseInput, ...] = (),
) -> Booking:
    client = Client(
        user=User(
            telegram_id=starts_at.toordinal(),
            username="test_client",
            display_name="Test Client",
        ),
        display_name="Test Client",
    )
    slot = Slot(
        starts_at=starts_at,
        ends_at=starts_at + timedelta(hours=1),
        place="Test studio",
    )
    booking = Booking(
        client=client,
        slot=slot,
        service="haircut",
        starts_at=starts_at,
        ends_at=starts_at + timedelta(hours=1),
        duration_minutes=60,
        place="Test studio",
        price_amount=Decimal("90.00"),
        final_amount=final_amount,
        status=status,
    )
    for expense in expenses:
        booking.expenses.append(
            BookingExpense(
                category=expense.category,
                amount=expense.amount,
                note=expense.note,
            )
        )
    session.add(booking)
    session.flush()
    return booking
