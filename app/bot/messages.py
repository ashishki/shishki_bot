"""Reusable client and admin message templates."""

from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from zoneinfo import ZoneInfo

from app.db.models import Booking

DEFAULT_MESSAGE_TIMEZONE = ZoneInfo("Asia/Tbilisi")


def booking_confirmation_message(
    booking: Booking,
    *,
    timezone: ZoneInfo = DEFAULT_MESSAGE_TIMEZONE,
) -> str:
    return "\n".join(
        [
            "Booking confirmed",
            f"Service: {booking.service}",
            f"Date: {_format_date(booking.starts_at, timezone)}",
            f"Time: {_format_time(booking.starts_at, timezone)}",
            f"Place: {booking.place}",
            f"Duration: {booking.duration_minutes} minutes",
            f"Price: {_format_money(booking.price_amount)} GEL",
            "To change or cancel, contact the stylist from the bot menu.",
        ]
    )


def booking_rescheduled_message(
    booking: Booking,
    *,
    timezone: ZoneInfo = DEFAULT_MESSAGE_TIMEZONE,
) -> str:
    return "\n".join(
        [
            "Booking rescheduled",
            f"Service: {booking.service}",
            f"New date: {_format_date(booking.starts_at, timezone)}",
            f"New time: {_format_time(booking.starts_at, timezone)}",
            f"Place: {booking.place}",
            f"Duration: {booking.duration_minutes} minutes",
            f"Price: {_format_money(booking.price_amount)} GEL",
        ]
    )


def booking_cancelled_message(
    booking: Booking,
    *,
    reason: str | None = None,
    timezone: ZoneInfo = DEFAULT_MESSAGE_TIMEZONE,
) -> str:
    lines = [
        "Booking cancelled",
        f"Service: {booking.service}",
        f"Date: {_format_date(booking.starts_at, timezone)}",
        f"Time: {_format_time(booking.starts_at, timezone)}",
        f"Place: {booking.place}",
    ]
    if reason:
        lines.append(f"Reason: {reason}")
    return "\n".join(lines)


def booking_updated_message(
    booking: Booking,
    *,
    timezone: ZoneInfo = DEFAULT_MESSAGE_TIMEZONE,
) -> str:
    return "\n".join(
        [
            "Booking updated",
            f"Service: {booking.service}",
            f"Date: {_format_date(booking.starts_at, timezone)}",
            f"Time: {_format_time(booking.starts_at, timezone)}",
            f"Place: {booking.place}",
            f"Duration: {booking.duration_minutes} minutes",
            f"Price: {_format_money(booking.price_amount)} GEL",
        ]
    )


def admin_new_booking_message(
    booking: Booking,
    *,
    timezone: ZoneInfo = DEFAULT_MESSAGE_TIMEZONE,
) -> str:
    return "\n".join(
        [
            "New booking",
            f"Service: {booking.service}",
            f"Date: {_format_date(booking.starts_at, timezone)}",
            f"Time: {_format_time(booking.starts_at, timezone)}",
            f"Place: {booking.place}",
            f"Price: {_format_money(booking.price_amount)} GEL",
        ]
    )


def _format_date(value: datetime, timezone: ZoneInfo) -> str:
    return _as_timezone(value, timezone).strftime("%Y-%m-%d")


def _format_time(value: datetime, timezone: ZoneInfo) -> str:
    return _as_timezone(value, timezone).strftime("%H:%M")


def _format_money(value: Decimal) -> str:
    return f"{value:.2f}".rstrip("0").rstrip(".")


def _as_timezone(value: datetime, timezone: ZoneInfo) -> datetime:
    if value.tzinfo is None:
        value = value.replace(tzinfo=timezone)
    return value.astimezone(timezone)
