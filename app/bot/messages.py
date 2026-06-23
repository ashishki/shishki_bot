"""Reusable client and admin message templates."""

from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from html import escape
from zoneinfo import ZoneInfo

from app.db.models import Booking

DEFAULT_MESSAGE_TIMEZONE = ZoneInfo("Asia/Tbilisi")


def booking_confirmation_message(
    booking: Booking,
    *,
    timezone: ZoneInfo = DEFAULT_MESSAGE_TIMEZONE,
    yandex_map_url: str | None = None,
    google_map_url: str | None = None,
    default_map_url: str | None = None,
) -> str:
    return "\n".join(
        [
            "Запись подтверждена",
            "",
            _html(_service_label(booking.service)),
            _format_date(booking.starts_at, timezone),
            _format_time(booking.starts_at, timezone),
            format_location_line(
                booking.place,
                yandex_map_url=yandex_map_url,
                google_map_url=google_map_url,
                default_map_url=default_map_url,
            ),
            f"{booking.duration_minutes} мин",
            f"{_format_money(booking.price_amount)} GEL",
            "",
            "Запись можно перенести или отменить в разделе «Моя запись».",
        ]
    )


def booking_rescheduled_message(
    booking: Booking,
    *,
    timezone: ZoneInfo = DEFAULT_MESSAGE_TIMEZONE,
    yandex_map_url: str | None = None,
    google_map_url: str | None = None,
    default_map_url: str | None = None,
) -> str:
    return "\n".join(
        [
            "Запись перенесена",
            "",
            _html(_service_label(booking.service)),
            _format_date(booking.starts_at, timezone),
            _format_time(booking.starts_at, timezone),
            format_location_line(
                booking.place,
                yandex_map_url=yandex_map_url,
                google_map_url=google_map_url,
                default_map_url=default_map_url,
            ),
            f"{booking.duration_minutes} мин",
            f"{_format_money(booking.price_amount)} GEL",
        ]
    )


def booking_cancelled_message(
    booking: Booking,
    *,
    reason: str | None = None,
    timezone: ZoneInfo = DEFAULT_MESSAGE_TIMEZONE,
    yandex_map_url: str | None = None,
    google_map_url: str | None = None,
    default_map_url: str | None = None,
) -> str:
    lines = [
        "Запись отменена",
        "",
        _html(_service_label(booking.service)),
        _format_date(booking.starts_at, timezone),
        _format_time(booking.starts_at, timezone),
        format_location_line(
            booking.place,
            yandex_map_url=yandex_map_url,
            google_map_url=google_map_url,
            default_map_url=default_map_url,
        ),
    ]
    if reason:
        lines.append(f"Причина: {_html(reason)}")
    return "\n".join(lines)


def booking_reminder_message(
    booking: Booking,
    *,
    reminder_kind: str,
    timezone: ZoneInfo = DEFAULT_MESSAGE_TIMEZONE,
    yandex_map_url: str | None = None,
    google_map_url: str | None = None,
    default_map_url: str | None = None,
) -> str:
    title = {
        "24h": "Напоминание: запись завтра",
        "3h": "Напоминание: запись сегодня",
    }.get(reminder_kind, "Напоминание о записи")
    return "\n".join(
        [
            title,
            "",
            _html(_service_label(booking.service)),
            _format_date(booking.starts_at, timezone),
            _format_time(booking.starts_at, timezone),
            format_location_line(
                booking.place,
                yandex_map_url=yandex_map_url,
                google_map_url=google_map_url,
                default_map_url=default_map_url,
            ),
            "",
            "Если нужно перенести или отменить запись, откройте «Моя запись».",
        ]
    )


def booking_updated_message(
    booking: Booking,
    *,
    timezone: ZoneInfo = DEFAULT_MESSAGE_TIMEZONE,
    yandex_map_url: str | None = None,
    google_map_url: str | None = None,
    default_map_url: str | None = None,
) -> str:
    return "\n".join(
        [
            "Запись обновлена",
            "",
            _html(_service_label(booking.service)),
            _format_date(booking.starts_at, timezone),
            _format_time(booking.starts_at, timezone),
            format_location_line(
                booking.place,
                yandex_map_url=yandex_map_url,
                google_map_url=google_map_url,
                default_map_url=default_map_url,
            ),
            f"{booking.duration_minutes} мин",
            f"{_format_money(booking.price_amount)} GEL",
        ]
    )


def admin_new_booking_message(
    booking: Booking,
    *,
    timezone: ZoneInfo = DEFAULT_MESSAGE_TIMEZONE,
    yandex_map_url: str | None = None,
    google_map_url: str | None = None,
    default_map_url: str | None = None,
) -> str:
    return "\n".join(
        [
            "Новая запись",
            f"Услуга: {_html(_service_label(booking.service))}",
            f"Дата: {_format_date(booking.starts_at, timezone)}",
            f"Время: {_format_time(booking.starts_at, timezone)}",
            format_location_line(
                booking.place,
                yandex_map_url=yandex_map_url,
                google_map_url=google_map_url,
                default_map_url=default_map_url,
            ),
            f"Цена: {_format_money(booking.price_amount)} GEL",
        ]
    )


def format_location_line(
    place: str,
    *,
    yandex_map_url: str | None = None,
    google_map_url: str | None = None,
    default_map_url: str | None = None,
) -> str:
    links: list[str] = []
    if yandex_map_url:
        links.append(_html_link("Yandex", yandex_map_url))
    if google_map_url:
        links.append(_html_link("Google", google_map_url))
    if not links and default_map_url:
        links.append(_html_link("Map", default_map_url))

    line = f"Адрес: {_html(place)}"
    if links:
        line = f"{line} | {' | '.join(links)}"
    return line


def _format_date(value: datetime, timezone: ZoneInfo) -> str:
    local_value = _as_timezone(value, timezone)
    return (
        f"{local_value.day} {_MONTHS_RU[local_value.month]}, "
        f"{_WEEKDAYS_RU[local_value.weekday()]}"
    )


def _format_time(value: datetime, timezone: ZoneInfo) -> str:
    return _as_timezone(value, timezone).strftime("%H:%M")


def _format_money(value: Decimal) -> str:
    return f"{value:.2f}".rstrip("0").rstrip(".")


def _as_timezone(value: datetime, timezone: ZoneInfo) -> datetime:
    if value.tzinfo is None:
        value = value.replace(tzinfo=timezone)
    return value.astimezone(timezone)


def _html(value: object) -> str:
    return escape(str(value), quote=False)


def _html_link(label: str, url: str) -> str:
    return f'<a href="{escape(url, quote=True)}">{_html(label)}</a>'


def _service_label(value: str) -> str:
    return "Стрижка" if value == "haircut" else value


_MONTHS_RU = {
    1: "января",
    2: "февраля",
    3: "марта",
    4: "апреля",
    5: "мая",
    6: "июня",
    7: "июля",
    8: "августа",
    9: "сентября",
    10: "октября",
    11: "ноября",
    12: "декабря",
}

_WEEKDAYS_RU = (
    "понедельник",
    "вторник",
    "среда",
    "четверг",
    "пятница",
    "суббота",
    "воскресенье",
)
