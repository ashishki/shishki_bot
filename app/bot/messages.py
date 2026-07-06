"""Reusable client and admin message templates."""

from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from html import escape
from zoneinfo import ZoneInfo

from app.db.models import Booking, Client
from app.services.booking import haircut_service_label

DEFAULT_MESSAGE_TIMEZONE = ZoneInfo("Asia/Tbilisi")
SALON_ENTRANCE_HINT_TEXT = (
    "Ориентир для входа: ищите вывеску ADITI BEAUTY CENTRE. "
    "Заходите в стеклянную дверь под вывеской, рядом с табличкой 22."
)


def booking_confirmation_message(
    booking: Booking,
    *,
    timezone: ZoneInfo = DEFAULT_MESSAGE_TIMEZONE,
    yandex_map_url: str | None = None,
    google_map_url: str | None = None,
    default_map_url: str | None = None,
    include_change_hint: bool = True,
    include_entrance_hint: bool = True,
) -> str:
    lines = [
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
    ]
    if include_entrance_hint:
        lines.extend(("", SALON_ENTRANCE_HINT_TEXT))
    lines.extend(
        [
            f"{booking.duration_minutes} мин",
            f"{_format_money(booking.price_amount)} GEL",
        ]
    )
    if include_change_hint:
        lines.extend(
            [
                "",
                "Если нужно изменить запись, откройте «Моя запись».",
            ]
        )
    return "\n".join(lines)


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
            *admin_booking_client_lines(booking),
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


def admin_booking_client_lines(booking: Booking) -> list[str]:
    client = booking.client
    if client is None:
        return ["Клиент: неизвестно"]

    lines = [
        f"Клиент: {_html(_client_display_name(client))}",
        f"ID клиента: {client.id}",
    ]
    if client.user and client.user.username:
        lines.append(f"Telegram: @{_html(client.user.username)}")
    contact_url = _client_contact_url(client)
    if contact_url:
        lines.append(f'Чат: <a href="{escape(contact_url, quote=True)}">открыть</a>')
    return lines


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
    return haircut_service_label(value)


def _client_display_name(client: Client) -> str:
    if client.display_name:
        return client.display_name
    if client.user and client.user.display_name:
        return client.user.display_name
    if client.user and client.user.username:
        return f"@{client.user.username}"
    return f"Клиент #{client.id}"


def _client_contact_url(client: Client) -> str | None:
    if client.user and client.user.username:
        return f"https://t.me/{client.user.username}"
    if client.user and client.user.telegram_id:
        return f"tg://user?id={client.user.telegram_id}"
    return None


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
