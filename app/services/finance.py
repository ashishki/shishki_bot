"""Finance operations for completion, expenses, and weekly revenue."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.models import (
    Booking,
    BookingExpense,
    BookingStatus,
    BookingStatusHistory,
    ExpenseCategory,
)

COMPLETABLE_BOOKING_STATUSES = (
    BookingStatus.CONFIRMED,
    BookingStatus.RESCHEDULED,
    BookingStatus.COMPLETED,
)
ZERO_MONEY = Decimal("0.00")


class FinanceServiceError(ValueError):
    """Raised when deterministic finance rules reject an operation."""


@dataclass(frozen=True, slots=True)
class ExpenseInput:
    category: ExpenseCategory
    amount: Decimal
    note: str | None = None


@dataclass(frozen=True, slots=True)
class WeeklyRevenueSummary:
    week_start: datetime
    week_end: datetime
    completed_count: int
    gross_revenue: Decimal
    expenses_by_category: dict[ExpenseCategory, Decimal]
    total_expenses: Decimal
    estimated_net: Decimal


def complete_booking(
    session: Session,
    *,
    booking_id: int,
    final_amount: Decimal,
    expenses: tuple[ExpenseInput, ...] = (),
    reason: str | None = None,
) -> Booking:
    booking = _get_booking(session, booking_id)
    _ensure_completable(booking)
    final_amount = _validate_money(final_amount, "final_amount")
    validated_expenses = tuple(
        ExpenseInput(
            category=expense.category,
            amount=_validate_money(expense.amount, "expense amount"),
            note=expense.note,
        )
        for expense in expenses
    )

    old_status = booking.status
    with session.begin_nested():
        booking.final_amount = final_amount
        if booking.status is not BookingStatus.COMPLETED:
            booking.status = BookingStatus.COMPLETED
            booking.status_history.append(
                BookingStatusHistory(
                    actor="admin",
                    old_status=old_status,
                    new_status=BookingStatus.COMPLETED,
                    reason=reason or "admin completed booking",
                )
            )
        for expense in validated_expenses:
            booking.expenses.append(
                BookingExpense(
                    category=expense.category,
                    amount=expense.amount,
                    note=expense.note,
                )
            )
        session.flush()

    from app.services.referrals import qualify_referral_for_booking

    qualify_referral_for_booking(session, booking=booking)
    return booking


def add_booking_expense(
    session: Session,
    *,
    booking_id: int,
    category: ExpenseCategory,
    amount: Decimal,
    note: str | None = None,
) -> BookingExpense:
    booking = _get_booking(session, booking_id)
    if booking.status is not BookingStatus.COMPLETED:
        raise FinanceServiceError("expenses can only be added to completed bookings")

    expense = BookingExpense(
        category=category,
        amount=_validate_money(amount, "expense amount"),
        note=note,
    )
    with session.begin_nested():
        booking.expenses.append(expense)
        session.flush()
    return expense


def weekly_revenue_summary(
    session: Session,
    *,
    week_start: datetime,
) -> WeeklyRevenueSummary:
    start = _as_utc(week_start)
    end = start + timedelta(days=7)
    completed_bookings = [
        booking
        for booking in session.scalars(
            select(Booking).where(
                Booking.status == BookingStatus.COMPLETED,
                Booking.final_amount.is_not(None),
            )
        )
        if start <= _as_utc(booking.starts_at) < end
    ]

    gross_revenue = sum(
        (booking.final_amount or ZERO_MONEY for booking in completed_bookings),
        ZERO_MONEY,
    )
    expenses_by_category = {category: ZERO_MONEY for category in ExpenseCategory}
    for booking in completed_bookings:
        for expense in booking.expenses:
            expenses_by_category[expense.category] += expense.amount

    total_expenses = sum(expenses_by_category.values(), ZERO_MONEY)
    return WeeklyRevenueSummary(
        week_start=start,
        week_end=end,
        completed_count=len(completed_bookings),
        gross_revenue=gross_revenue,
        expenses_by_category=expenses_by_category,
        total_expenses=total_expenses,
        estimated_net=gross_revenue - total_expenses,
    )


def _get_booking(session: Session, booking_id: int) -> Booking:
    booking = session.get(Booking, booking_id)
    if booking is None:
        raise FinanceServiceError(f"Booking not found: {booking_id}")
    return booking


def _ensure_completable(booking: Booking) -> None:
    if booking.status not in COMPLETABLE_BOOKING_STATUSES:
        raise FinanceServiceError(
            f"Booking cannot be completed from status: {booking.status.value}"
        )


def _validate_money(amount: Decimal, field_name: str) -> Decimal:
    if amount < ZERO_MONEY:
        raise FinanceServiceError(f"{field_name} must not be negative")
    return amount


def _as_utc(value: datetime) -> datetime:
    if value.tzinfo is None:
        return value.replace(tzinfo=UTC)
    return value.astimezone(UTC)
