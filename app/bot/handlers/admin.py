"""Admin command and callback guards."""

from __future__ import annotations

from collections.abc import Callable
from contextlib import AbstractAsyncContextManager
from dataclasses import dataclass
from datetime import UTC, date, datetime, timedelta
from decimal import Decimal
from html import escape

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import Session

from app.bot.keyboards import (
    ADMIN_CALLBACK_PREFIX,
    AdminMenuAction,
    MenuButton,
    admin_callback_data,
    admin_menu_buttons,
    parse_admin_callback_data,
)
from app.bot.messages import (
    booking_cancelled_message,
    booking_confirmation_message,
    booking_rescheduled_message,
    booking_updated_message,
)
from app.config import Settings
from app.db.models import (
    Booking,
    BookingStatus,
    Client,
    DeliveryStatus,
    NotificationLog,
    ReferralBonusStatus,
    Slot,
    User,
)
from app.services.booking import (
    ACTIVE_BOOKING_STATUSES,
    BookingServiceError,
    SlotUnavailableError,
    cancel_booking_by_admin,
    create_manual_booking,
    haircut_service_label,
    list_available_slots,
    reschedule_booking,
    update_booking_details_by_admin,
)
from app.services.clients import ClientCard, client_card_summary
from app.services.finance import (
    ExpenseInput,
    WeeklyRevenueSummary,
    complete_booking,
    weekly_revenue_summary,
)
from app.services.notifications import NotificationSender, send_client_notification
from app.services.referrals import (
    REFERRAL_BONUS_THRESHOLD,
    mark_referral_bonus_awarded,
    pending_referral_bonuses,
    referral_progress,
)

ADMIN_MENU_TEXT = "Админ-панель"
ADMIN_ACCESS_DENIED_TEXT = "Нет доступа к админке"
UNKNOWN_ADMIN_ACTION_TEXT = "Неизвестное действие"
NO_CLIENTS_TEXT = "Клиентов пока нет. Они появятся после первой записи через бота."
CLIENT_NOT_FOUND_TEXT = "Клиент не найден."
NO_BOOKINGS_TEXT = "На эту дату записей пока нет."
BOOKING_NOT_FOUND_TEXT = "Запись не найдена."
NO_AVAILABLE_SLOTS_TEXT = "Свободных слотов пока нет."
NO_REFERRAL_BONUSES_TEXT = "Бонусов к выдаче пока нет."
ADMIN_ACTIVE_BOOKING_STATUSES = (
    BookingStatus.CONFIRMED,
    BookingStatus.RESCHEDULED,
)
MANUAL_BOOKING_HELP_TEXT = "\n".join(
    [
        "Создать ручную запись:",
        "/book <client_id|@username> <YYYY-MM-DD> <HH:MM> <минуты> <цена> <услуга>",
        "",
        "Пример:",
        "/book @client 2026-06-28 15:00 180 250 Окрашивание",
        "",
        "ID и username видны в «Клиенты» -> карточка клиента.",
    ]
)
SLOT_SCHEDULE_HELP_TEXT = "\n".join(
    [
        "Рабочее время:",
        "/open <YYYY-MM-DD> <HH:MM>",
        "/open_day <YYYY-MM-DD> <HH:MM> <HH:MM>",
        "/close <YYYY-MM-DD> <HH:MM>",
        "/close_day <YYYY-MM-DD> <HH:MM>",
        "",
        "Примеры:",
        "/open 2026-07-12 10:00",
        "/open_day 2026-07-12 10:00 20:00",
        "/close 2026-07-04 16:00",
        "/close_day 2026-07-04 16:00",
    ]
)
SLOT_CLOSING_HELP_TEXT = SLOT_SCHEDULE_HELP_TEXT
WORKING_TIME_DAYS_TO_SHOW = 14
WORKING_DAY_PRESETS = (
    ("10:00", "20:00"),
    ("12:00", "20:00"),
    ("13:00", "20:00"),
)
WORKING_HOUR_STARTS = (
    "10:00",
    "11:00",
    "12:00",
    "13:00",
    "14:00",
    "15:00",
    "16:00",
    "17:00",
    "18:00",
    "19:00",
)
CLOSE_REST_PRESETS = ("16:00", "17:00", "18:00")
WORKING_OPEN_DAY = "od"
WORKING_CLOSE_DAY = "cd"
WORKING_OPEN_SLOT = "os"
WORKING_CLOSE_SLOT = "cs"


class AdminAccessDenied(PermissionError):
    """Raised when a Telegram user is not allowed to use admin controls."""


@dataclass(frozen=True, slots=True)
class AdminMenuResponse:
    text: str
    buttons: tuple[MenuButton, ...]


@dataclass(frozen=True, slots=True)
class AdminActionResponse:
    action: AdminMenuAction
    text: str


@dataclass(frozen=True, slots=True)
class AdminBookingMutationResponse:
    booking: Booking
    notification_log: NotificationLog | None = None


@dataclass(frozen=True, slots=True)
class AdminRevenueResponse:
    summary: WeeklyRevenueSummary


@dataclass(frozen=True, slots=True)
class AdminClientCardResponse:
    client_card: ClientCard


@dataclass(frozen=True, slots=True)
class AdminRuntimeButton:
    label: str
    callback_data: str | None = None
    url: str | None = None


@dataclass(frozen=True, slots=True)
class AdminRuntimeResponse:
    text: str
    buttons: tuple[AdminRuntimeButton, ...] = ()


@dataclass(frozen=True, slots=True)
class AdminNotificationAttempt:
    response: AdminRuntimeResponse
    booking_id: int
    client_id: int
    recipient_telegram_id: int | None
    kind: str
    text: str


@dataclass(frozen=True, slots=True)
class ManualBookingCommand:
    client_ref: str
    starts_at: datetime
    duration_minutes: int
    price_amount: Decimal
    service: str


@dataclass(frozen=True, slots=True)
class WorkingTimeOperation:
    operation: str
    selected_date: date
    start_time: str
    end_time: str | None = None


def is_admin_user(telegram_user_id: int | None, settings: Settings) -> bool:
    return telegram_user_id in settings.admin_telegram_ids


def require_admin_user(telegram_user_id: int | None, settings: Settings) -> None:
    if not is_admin_user(telegram_user_id, settings):
        raise AdminAccessDenied("Admin access denied")


def handle_admin_menu_command(
    telegram_user_id: int | None,
    settings: Settings,
) -> AdminMenuResponse:
    require_admin_user(telegram_user_id, settings)
    return AdminMenuResponse(text=ADMIN_MENU_TEXT, buttons=admin_menu_buttons())


def handle_admin_dashboard(
    session: Session,
    settings: Settings,
    *,
    telegram_user_id: int | None,
    now: datetime | None = None,
) -> AdminRuntimeResponse:
    require_admin_user(telegram_user_id, settings)
    current_time = now or datetime.now(UTC)
    today = _datetime_local(current_time, settings).date()
    today_bookings = tuple(
        booking
        for booking in _bookings_for_date(session, settings, today)
        if booking.status in ADMIN_ACTIVE_BOOKING_STATUSES
    )
    upcoming_bookings = _upcoming_bookings(session, settings, now=current_time)
    upcoming_client_count = len({booking.client_id for booking in upcoming_bookings})
    client_count = _client_count(session)
    available_slot_count = len(list_available_slots(session, now=current_time))
    revenue = weekly_revenue_summary(
        session,
        week_start=_week_start(current_time, settings),
    )
    pending_bonus_count = len(pending_referral_bonuses(session))

    lines = [
        ADMIN_MENU_TEXT,
        "",
        f"Сегодня записей: {len(today_bookings)}",
        f"Ближайших записей: {len(upcoming_bookings)}",
        f"Свободных слотов: {available_slot_count}",
        f"Клиентов: {client_count}",
        f"Клиентов с будущей записью: {upcoming_client_count}",
        (
            "Неделя: "
            f"{revenue.completed_count} завершено, "
            f"{_format_money(revenue.gross_revenue)} GEL"
        ),
        f"Бонусов к выдаче: {pending_bonus_count}",
        "",
        "Ближайшие записи:",
    ]
    if upcoming_bookings:
        lines.extend(
            _booking_line(booking, settings) for booking in upcoming_bookings[:5]
        )
    else:
        lines.append("нет")

    return AdminRuntimeResponse(
        text="\n".join(lines),
        buttons=_admin_dashboard_buttons(),
    )


def handle_admin_metrics_dashboard(
    session: Session,
    settings: Settings,
    *,
    telegram_user_id: int | None,
    now: datetime | None = None,
) -> AdminRuntimeResponse:
    require_admin_user(telegram_user_id, settings)
    current_time = now or datetime.now(UTC)
    revenue = weekly_revenue_summary(
        session,
        week_start=_week_start(current_time, settings),
    )
    client_count = _client_count(session)
    upcoming_client_count = len(
        {
            booking.client_id
            for booking in _upcoming_bookings(session, settings, now=current_time)
        }
    )
    client_cards = _client_metric_cards(session)
    completed_client_count = sum(1 for card in client_cards if card.visit_count)

    lines = [
        "Метрики",
        "",
        f"Клиентов всего: {client_count}",
        f"Клиентов с будущей записью: {upcoming_client_count}",
        f"Клиентов с завершенными визитами: {completed_client_count}",
        "",
        "Неделя:",
        f"Завершено визитов: {revenue.completed_count}",
        f"Выручка: {_format_money(revenue.gross_revenue)} GEL",
        f"Расходы: {_format_money(revenue.total_expenses)} GEL",
        f"Нетто: {_format_money(revenue.estimated_net)} GEL",
        "",
        "Топ клиентов:",
    ]
    top_clients = tuple(card for card in client_cards if card.visit_count)[:5]
    if top_clients:
        lines.extend(
            (
                f"- {_html(card.display_name)} #{card.client_id}: "
                f"{card.visit_count} визитов, {_format_money(card.total_spent)} GEL"
            )
            for card in top_clients
        )
    else:
        lines.append("пока нет завершенных визитов")

    buttons = tuple(
        AdminRuntimeButton(
            label=f"Клиент #{card.client_id}",
            callback_data=admin_callback_data(
                AdminMenuAction.CLIENT_CARD,
                card.client_id,
            ),
        )
        for card in top_clients
    )
    return AdminRuntimeResponse(
        text="\n".join(lines),
        buttons=buttons
        + (
            AdminRuntimeButton(
                label="Все клиенты",
                callback_data=admin_callback_data(AdminMenuAction.CLIENTS),
            ),
            _admin_menu_button(),
        ),
    )


def handle_admin_callback(
    telegram_user_id: int | None,
    settings: Settings,
    callback_payload: str | None,
) -> AdminActionResponse:
    require_admin_user(telegram_user_id, settings)
    action = parse_admin_callback_data(callback_payload)
    return AdminActionResponse(
        action=action,
        text=f"Admin action: {action.value}",
    )


def build_admin_menu_response(
    telegram_user_id: int | None,
    settings: Settings,
) -> AdminMenuResponse:
    return handle_admin_menu_command(telegram_user_id, settings)


def resolve_admin_action(
    telegram_user_id: int | None,
    settings: Settings,
    callback_payload: str | None,
) -> AdminMenuAction:
    return handle_admin_callback(telegram_user_id, settings, callback_payload).action


def handle_admin_manual_booking(
    session: Session,
    settings: Settings,
    *,
    telegram_user_id: int | None,
    client_id: int,
    slot_id: int,
    service: str,
    duration_minutes: int,
    price_amount: Decimal,
    place: str | None = None,
    notes: str | None = None,
) -> AdminBookingMutationResponse:
    require_admin_user(telegram_user_id, settings)
    booking = create_manual_booking(
        session,
        client_id=client_id,
        slot_id=slot_id,
        service=service,
        duration_minutes=duration_minutes,
        price_amount=price_amount,
        place=place,
        notes=notes,
    )
    return AdminBookingMutationResponse(booking=booking)


def handle_admin_manual_booking_command(
    session: Session,
    settings: Settings,
    *,
    telegram_user_id: int | None,
    command_text: str | None,
) -> AdminNotificationAttempt:
    require_admin_user(telegram_user_id, settings)
    command = _parse_manual_booking_command(command_text, settings)
    client = _resolve_client_reference(session, command.client_ref)
    slot = _get_or_create_manual_slot(
        session,
        settings,
        starts_at=command.starts_at,
    )
    booking = create_manual_booking(
        session,
        client_id=client.id,
        slot_id=slot.id,
        service=command.service,
        duration_minutes=command.duration_minutes,
        price_amount=command.price_amount,
    )
    text = booking_confirmation_message(
        booking,
        timezone=settings.timezone_info,
        **_settings_location_links(settings),
    )
    return AdminNotificationAttempt(
        response=AdminRuntimeResponse(
            text="Запись создана\n" + _booking_line(booking, settings),
            buttons=(
                _booking_detail_button(booking, settings),
                _schedule_date_button(_booking_local_date(booking, settings)),
                _admin_menu_button(),
            ),
        ),
        booking_id=booking.id,
        client_id=booking.client_id,
        recipient_telegram_id=_recipient_telegram_id(booking),
        kind="booking_confirmation",
        text=text,
    )


def handle_admin_close_slot_command(
    session: Session,
    settings: Settings,
    *,
    telegram_user_id: int | None,
    command_text: str | None,
) -> AdminRuntimeResponse:
    require_admin_user(telegram_user_id, settings)
    starts_at = _parse_slot_closing_command(command_text, settings, "/close")
    slot = _find_slot_by_local_start(session, settings, starts_at=starts_at)
    if slot is None:
        return AdminRuntimeResponse(
            text="Слот не найден.\n\n" + SLOT_CLOSING_HELP_TEXT,
            buttons=(_admin_menu_button(),),
        )

    booking = _active_booking_for_slot(session, slot)
    if booking is not None:
        return AdminRuntimeResponse(
            text=(
                "Не закрываю: на это время есть активная запись.\n"
                + _booking_line(booking, settings)
            ),
            buttons=(
                _booking_detail_button(booking, settings),
                _schedule_date_button(_slot_local_date(slot, settings)),
                _admin_menu_button(),
            ),
        )
    if slot.is_blocked:
        return AdminRuntimeResponse(
            text=(
                "Слот уже закрыт: "
                f"{_format_datetime(_slot_local_start(slot, settings))}"
            ),
            buttons=(
                _schedule_date_button(_slot_local_date(slot, settings)),
                _admin_menu_button(),
            ),
        )

    _block_slot(slot, note="closed by admin command")
    session.flush()
    return AdminRuntimeResponse(
        text=f"Слот закрыт: {_format_datetime(_slot_local_start(slot, settings))}",
        buttons=(
            _schedule_date_button(_slot_local_date(slot, settings)),
            _admin_menu_button(),
        ),
    )


def handle_admin_close_day_command(
    session: Session,
    settings: Settings,
    *,
    telegram_user_id: int | None,
    command_text: str | None,
) -> AdminRuntimeResponse:
    require_admin_user(telegram_user_id, settings)
    starts_at = _parse_slot_closing_command(command_text, settings, "/close_day")
    selected_date = starts_at.date()
    local_start = starts_at.time()
    slots = tuple(
        slot
        for slot in _slots_for_date(session, settings, selected_date)
        if _slot_local_start(slot, settings).time() >= local_start
    )
    if not slots:
        return AdminRuntimeResponse(
            text="На эту дату и время слоты не найдены.\n\n" + SLOT_CLOSING_HELP_TEXT,
            buttons=(_admin_menu_button(),),
        )

    closed_count = 0
    already_closed_count = 0
    skipped_bookings: list[Booking] = []
    for slot in slots:
        booking = _active_booking_for_slot(session, slot)
        if booking is not None:
            skipped_bookings.append(booking)
            continue
        if slot.is_blocked:
            already_closed_count += 1
            continue
        _block_slot(slot, note="rest of day closed by admin command")
        closed_count += 1
    session.flush()

    lines = [
        (
            "Закрыл свободные слоты: "
            f"{_format_date_label(selected_date)} с {starts_at:%H:%M}, "
            f"{closed_count} шт."
        )
    ]
    if already_closed_count:
        lines.append(f"Уже были закрыты: {already_closed_count}.")
    if skipped_bookings:
        lines.append("Не тронул слоты с активными записями:")
        lines.extend(_booking_line(booking, settings) for booking in skipped_bookings)
    return AdminRuntimeResponse(
        text="\n".join(lines),
        buttons=(
            _schedule_date_button(selected_date),
            _admin_menu_button(),
        ),
    )


def handle_admin_open_slot_command(
    session: Session,
    settings: Settings,
    *,
    telegram_user_id: int | None,
    command_text: str | None,
) -> AdminRuntimeResponse:
    require_admin_user(telegram_user_id, settings)
    starts_at = _parse_slot_opening_command(command_text, settings, "/open")
    slot, status = _open_slot(
        session,
        settings,
        starts_at=starts_at,
        note="opened by admin command",
    )
    session.flush()

    if status == "created":
        text = "Слот создан и открыт: "
    elif status == "reopened":
        text = "Слот открыт: "
    else:
        text = "Слот уже открыт: "

    return AdminRuntimeResponse(
        text=text + _format_datetime(_slot_local_start(slot, settings)),
        buttons=(
            _schedule_date_button(_slot_local_date(slot, settings)),
            _admin_menu_button(),
        ),
    )


def handle_admin_open_day_command(
    session: Session,
    settings: Settings,
    *,
    telegram_user_id: int | None,
    command_text: str | None,
) -> AdminRuntimeResponse:
    require_admin_user(telegram_user_id, settings)
    starts_at, ends_at = _parse_slot_opening_day_command(
        command_text,
        settings,
        "/open_day",
    )
    selected_date = starts_at.date()

    created_count = 0
    reopened_count = 0
    already_open_count = 0
    active_bookings: list[Booking] = []
    current_start = starts_at
    while current_start < ends_at:
        slot, status = _open_slot(
            session,
            settings,
            starts_at=current_start,
            note="opened by admin day command",
        )
        if status == "created":
            created_count += 1
        elif status == "reopened":
            reopened_count += 1
        else:
            already_open_count += 1

        booking = _active_booking_for_slot(session, slot)
        if booking is not None and booking not in active_bookings:
            active_bookings.append(booking)
        current_start += timedelta(hours=1)
    session.flush()

    lines = [
        (
            "Рабочий день открыт: "
            f"{_format_date_label(selected_date)} "
            f"{starts_at:%H:%M}-{ends_at:%H:%M}"
        ),
        f"Создано слотов: {created_count}.",
        f"Открыто закрытых: {reopened_count}.",
    ]
    if already_open_count:
        lines.append(f"Уже были открыты: {already_open_count}.")
    if active_bookings:
        lines.append("На часть времени уже есть активные записи:")
        lines.extend(_booking_line(booking, settings) for booking in active_bookings)

    return AdminRuntimeResponse(
        text="\n".join(lines),
        buttons=(
            _schedule_date_button(selected_date),
            _admin_menu_button(),
        ),
    )


def handle_admin_reschedule_booking(
    session: Session,
    settings: Settings,
    *,
    sender: NotificationSender,
    telegram_user_id: int | None,
    booking_id: int,
    new_slot_id: int,
    reason: str | None = None,
) -> AdminBookingMutationResponse:
    require_admin_user(telegram_user_id, settings)
    booking = reschedule_booking(
        session,
        booking_id=booking_id,
        new_slot_id=new_slot_id,
        reason=reason,
    )
    notification_log = send_client_notification(
        session,
        sender=sender,
        booking=booking,
        kind="booking_rescheduled",
        text=booking_rescheduled_message(
            booking,
            timezone=settings.timezone_info,
            **_settings_location_links(settings),
        ),
    )
    return AdminBookingMutationResponse(
        booking=booking,
        notification_log=notification_log,
    )


def handle_admin_cancel_booking(
    session: Session,
    settings: Settings,
    *,
    sender: NotificationSender,
    telegram_user_id: int | None,
    booking_id: int,
    reason: str | None = None,
) -> AdminBookingMutationResponse:
    require_admin_user(telegram_user_id, settings)
    booking = cancel_booking_by_admin(
        session,
        booking_id=booking_id,
        reason=reason,
    )
    notification_log = send_client_notification(
        session,
        sender=sender,
        booking=booking,
        kind="booking_cancelled",
        text=booking_cancelled_message(
            booking,
            reason=reason,
            timezone=settings.timezone_info,
            **_settings_location_links(settings),
        ),
    )
    return AdminBookingMutationResponse(
        booking=booking,
        notification_log=notification_log,
    )


def handle_admin_update_booking_details(
    session: Session,
    settings: Settings,
    *,
    sender: NotificationSender | None = None,
    telegram_user_id: int | None,
    booking_id: int,
    service: str | None = None,
    duration_minutes: int | None = None,
    price_amount: Decimal | None = None,
    place: str | None = None,
    notes: str | None = None,
) -> AdminBookingMutationResponse:
    require_admin_user(telegram_user_id, settings)
    should_notify = any(
        value is not None for value in (service, duration_minutes, price_amount, place)
    )
    if should_notify and sender is None:
        raise ValueError("sender is required for client-visible booking changes")

    booking = update_booking_details_by_admin(
        session,
        booking_id=booking_id,
        service=service,
        duration_minutes=duration_minutes,
        price_amount=price_amount,
        place=place,
        notes=notes,
    )
    notification_log = None
    if should_notify:
        notification_log = send_client_notification(
            session,
            sender=sender,
            booking=booking,
            kind="booking_updated",
            text=booking_updated_message(
                booking,
                timezone=settings.timezone_info,
                **_settings_location_links(settings),
            ),
        )
    return AdminBookingMutationResponse(
        booking=booking,
        notification_log=notification_log,
    )


def handle_admin_complete_booking(
    session: Session,
    settings: Settings,
    *,
    telegram_user_id: int | None,
    booking_id: int,
    final_amount: Decimal,
    expenses: tuple[ExpenseInput, ...] = (),
    reason: str | None = None,
) -> AdminBookingMutationResponse:
    require_admin_user(telegram_user_id, settings)
    booking = complete_booking(
        session,
        booking_id=booking_id,
        final_amount=final_amount,
        expenses=expenses,
        reason=reason,
    )
    return AdminBookingMutationResponse(booking=booking)


def handle_admin_weekly_revenue(
    session: Session,
    settings: Settings,
    *,
    telegram_user_id: int | None,
    week_start: datetime,
) -> AdminRevenueResponse:
    require_admin_user(telegram_user_id, settings)
    return AdminRevenueResponse(
        summary=weekly_revenue_summary(session, week_start=week_start)
    )


def handle_admin_client_card(
    session: Session,
    settings: Settings,
    *,
    telegram_user_id: int | None,
    client_id: int,
) -> AdminClientCardResponse:
    require_admin_user(telegram_user_id, settings)
    return AdminClientCardResponse(
        client_card=client_card_summary(session, client_id=client_id)
    )


def handle_admin_clients_list(
    session: Session,
    settings: Settings,
    *,
    telegram_user_id: int | None,
) -> AdminRuntimeResponse:
    require_admin_user(telegram_user_id, settings)
    clients = tuple(
        session.scalars(select(Client).join(User, isouter=True).order_by(Client.id))
    )
    if not clients:
        return AdminRuntimeResponse(text=NO_CLIENTS_TEXT)

    return AdminRuntimeResponse(
        text="Клиенты",
        buttons=tuple(
            AdminRuntimeButton(
                label=_client_button_label(client),
                callback_data=admin_callback_data(
                    AdminMenuAction.CLIENT_CARD,
                    client.id,
                ),
            )
            for client in clients
        ),
    )


def handle_admin_client_card_view(
    session: Session,
    settings: Settings,
    *,
    telegram_user_id: int | None,
    client_id: int,
    now: datetime | None = None,
) -> AdminRuntimeResponse:
    require_admin_user(telegram_user_id, settings)
    client = session.get(Client, client_id)
    if client is None:
        return AdminRuntimeResponse(
            text=CLIENT_NOT_FOUND_TEXT,
            buttons=(_clients_button(),),
        )

    active_bookings = _client_bookings(
        session,
        client_id=client.id,
        active=True,
        now=now,
    )
    history_bookings = _client_bookings(
        session,
        client_id=client.id,
        active=False,
        now=now,
    )
    contact_url = _client_contact_url(client)

    lines = [
        f"Карточка клиента: {_html(_client_display_name(client))}",
        f"ID клиента: {client.id}",
    ]
    if client.user and client.user.username:
        lines.append(f"Telegram: @{_html(client.user.username)}")
    if contact_url:
        lines.append(f'Чат: <a href="{escape(contact_url, quote=True)}">открыть</a>')
    if client.notes:
        lines.append(f"Заметки: {_html(client.notes)}")

    progress = referral_progress(session, client_id=client.id)
    lines.append("")
    lines.append("Рекомендации:")
    if progress.code:
        lines.append(f"Код: {_html(progress.code)}")
    else:
        lines.append("Код: клиент еще не запрашивал ссылку")
    lines.append(f"Засчитано: {progress.qualified_count}/{REFERRAL_BONUS_THRESHOLD}")
    lines.append(f"Ожидают визита: {progress.pending_count}")
    lines.append(f"Бонусов к выдаче: {progress.pending_bonus_count}")
    lines.append(f"Бонусов выдано: {progress.awarded_bonus_count}")

    lines.append("")
    lines.append("Текущая запись:")
    if active_bookings:
        lines.extend(_booking_line(booking, settings) for booking in active_bookings)
    else:
        lines.append("нет")

    lines.append("")
    lines.append("История:")
    if history_bookings:
        lines.extend(
            _booking_line(booking, settings) for booking in history_bookings[:5]
        )
    else:
        lines.append("нет")

    buttons = []
    if contact_url:
        buttons.append(AdminRuntimeButton(label="Открыть чат", url=contact_url))
    if progress.pending_bonus_count:
        buttons.append(
            AdminRuntimeButton(
                label="Бонусы",
                callback_data=admin_callback_data(AdminMenuAction.REFERRAL_BONUSES),
            )
        )
    buttons.extend((_clients_button(), _admin_menu_button()))
    return AdminRuntimeResponse(text="\n".join(lines), buttons=tuple(buttons))


def handle_admin_referral_bonuses(
    session: Session,
    settings: Settings,
    *,
    telegram_user_id: int | None,
) -> AdminRuntimeResponse:
    require_admin_user(telegram_user_id, settings)
    bonuses = pending_referral_bonuses(session)
    if not bonuses:
        return AdminRuntimeResponse(
            text=NO_REFERRAL_BONUSES_TEXT,
            buttons=(_admin_menu_button(),),
        )

    lines = ["Бонусы к выдаче"]
    buttons: list[AdminRuntimeButton] = []
    for bonus in bonuses:
        client = bonus.client
        lines.extend(
            [
                "",
                f"#{bonus.id} {_html(_client_display_name(client))}",
                f"Клиент ID: {client.id}",
                f"Засчитано рекомендаций: {bonus.referral_count}",
                f"Подарок: {_html(bonus.reward_label)}",
            ]
        )
        buttons.append(
            AdminRuntimeButton(
                label=f"Выдано #{bonus.id}",
                callback_data=admin_callback_data(
                    AdminMenuAction.MARK_REFERRAL_BONUS_AWARDED,
                    bonus.id,
                ),
            )
        )
        buttons.append(
            AdminRuntimeButton(
                label=f"Клиент #{client.id}",
                callback_data=admin_callback_data(
                    AdminMenuAction.CLIENT_CARD,
                    client.id,
                ),
            )
        )

    buttons.append(_admin_menu_button())
    return AdminRuntimeResponse(text="\n".join(lines), buttons=tuple(buttons))


def handle_admin_mark_referral_bonus_awarded(
    session: Session,
    settings: Settings,
    *,
    telegram_user_id: int | None,
    bonus_id: int,
) -> AdminRuntimeResponse:
    require_admin_user(telegram_user_id, settings)
    bonus = mark_referral_bonus_awarded(session, bonus_id=bonus_id)
    client = bonus.client
    status = (
        "выдан" if bonus.status is ReferralBonusStatus.AWARDED else bonus.status.value
    )
    return AdminRuntimeResponse(
        text="\n".join(
            [
                f"Бонус #{bonus.id}: {status}",
                f"Клиент: {_html(_client_display_name(client))} #{client.id}",
                f"Подарок: {_html(bonus.reward_label)}",
            ]
        ),
        buttons=(
            AdminRuntimeButton(
                label="Карточка клиента",
                callback_data=admin_callback_data(
                    AdminMenuAction.CLIENT_CARD,
                    client.id,
                ),
            ),
            AdminRuntimeButton(
                label="Бонусы",
                callback_data=admin_callback_data(AdminMenuAction.REFERRAL_BONUSES),
            ),
            _admin_menu_button(),
        ),
    )


def handle_admin_working_time_dates(
    session: Session,
    settings: Settings,
    *,
    telegram_user_id: int | None,
    start_date: date | None = None,
    days: int = WORKING_TIME_DAYS_TO_SHOW,
) -> AdminRuntimeResponse:
    require_admin_user(telegram_user_id, settings)
    first_date = start_date or datetime.now(settings.timezone_info).date()
    dates = tuple(first_date + timedelta(days=offset) for offset in range(days))
    return AdminRuntimeResponse(
        text="\n".join(
            [
                "Рабочее время",
                "",
                "Выберите дату. Внутри будут готовые кнопки: открыть день, "
                "закрыть день, закрыть остаток дня или открыть/закрыть час.",
                "",
                "Команды с форматом остаются быстрым режимом:",
                "/open_day 2026-07-12 10:00 20:00",
                "/close_day 2026-07-12 16:00",
            ]
        ),
        buttons=tuple(
            _working_time_date_button(
                value,
                label=_working_time_date_label(session, settings, value),
            )
            for value in dates
        )
        + (_admin_menu_button(),),
    )


def handle_admin_working_time_date_view(
    session: Session,
    settings: Settings,
    *,
    telegram_user_id: int | None,
    selected_date: date,
) -> AdminRuntimeResponse:
    require_admin_user(telegram_user_id, settings)
    slots = _slots_for_date(session, settings, selected_date)
    active_bookings = tuple(
        booking
        for booking in _bookings_for_date(session, settings, selected_date)
        if booking.status in ADMIN_ACTIVE_BOOKING_STATUSES
    )
    open_count = sum(1 for slot in slots if not slot.is_blocked)
    blocked_count = sum(1 for slot in slots if slot.is_blocked)
    lines = [
        f"Рабочее время: {_format_date_label(selected_date)}",
        f"Слотов: {len(slots)}",
        f"Открыто: {open_count}",
        f"Закрыто: {blocked_count}",
        f"Активных записей: {len(active_bookings)}",
        "",
        "Выберите готовое действие. Перед изменением будет подтверждение.",
    ]
    if active_bookings:
        lines.append("")
        lines.append("Записи:")
        lines.extend(_booking_line(booking, settings) for booking in active_bookings)

    buttons: list[AdminRuntimeButton] = []
    for start_time, end_time in WORKING_DAY_PRESETS:
        if not _is_future_working_time(selected_date, start_time, settings):
            continue
        buttons.append(
            _working_time_confirm_button(
                label=f"Открыть день {start_time}-{end_time}",
                operation=WORKING_OPEN_DAY,
                selected_date=selected_date,
                start_time=start_time,
                end_time=end_time,
            )
        )

    today = datetime.now(settings.timezone_info).date()
    if slots and selected_date > today:
        buttons.append(
            _working_time_confirm_button(
                label="Закрыть весь день",
                operation=WORKING_CLOSE_DAY,
                selected_date=selected_date,
                start_time="00:00",
            )
        )
    for close_start in CLOSE_REST_PRESETS:
        if not slots:
            continue
        if _is_future_working_time(selected_date, close_start, settings):
            buttons.append(
                _working_time_confirm_button(
                    label=f"Закрыть с {close_start}",
                    operation=WORKING_CLOSE_DAY,
                    selected_date=selected_date,
                    start_time=close_start,
                )
            )

    buttons.extend(
        _working_time_hour_buttons(session, settings, selected_date=selected_date)
    )
    buttons.extend((_working_time_dates_button(), _admin_menu_button()))
    return AdminRuntimeResponse(text="\n".join(lines), buttons=tuple(buttons))


def handle_admin_working_time_confirm_prompt(
    session: Session,
    settings: Settings,
    *,
    telegram_user_id: int | None,
    value: str | None,
) -> AdminRuntimeResponse:
    require_admin_user(telegram_user_id, settings)
    operation = _parse_working_time_operation(value)
    return AdminRuntimeResponse(
        text="\n".join(
            [
                "Подтвердите действие",
                "",
                _working_time_operation_summary(operation),
            ]
        ),
        buttons=(
            AdminRuntimeButton(
                label="Да, выполнить",
                callback_data=admin_callback_data(
                    AdminMenuAction.WORKING_TIME_APPLY,
                    _working_time_operation_value(operation),
                ),
            ),
            _working_time_date_button(
                operation.selected_date,
                label="Назад к дате",
            ),
            _working_time_dates_button(),
            _admin_menu_button(),
        ),
    )


def handle_admin_working_time_apply(
    session: Session,
    settings: Settings,
    *,
    telegram_user_id: int | None,
    value: str | None,
) -> AdminRuntimeResponse:
    require_admin_user(telegram_user_id, settings)
    operation = _parse_working_time_operation(value)
    command_text = _working_time_command_text(operation)
    if operation.operation == WORKING_OPEN_DAY:
        return handle_admin_open_day_command(
            session,
            settings,
            telegram_user_id=telegram_user_id,
            command_text=command_text,
        )
    if operation.operation == WORKING_OPEN_SLOT:
        return handle_admin_open_slot_command(
            session,
            settings,
            telegram_user_id=telegram_user_id,
            command_text=command_text,
        )
    if operation.operation == WORKING_CLOSE_DAY:
        return handle_admin_close_day_command(
            session,
            settings,
            telegram_user_id=telegram_user_id,
            command_text=command_text,
        )
    if operation.operation == WORKING_CLOSE_SLOT:
        return handle_admin_close_slot_command(
            session,
            settings,
            telegram_user_id=telegram_user_id,
            command_text=command_text,
        )
    raise ValueError("Неизвестное действие рабочего времени.")


def handle_admin_schedule_dates(
    session: Session,
    settings: Settings,
    *,
    telegram_user_id: int | None,
    start_date: date,
    days: int = 7,
) -> AdminRuntimeResponse:
    require_admin_user(telegram_user_id, settings)
    end_date = start_date + timedelta(days=days)
    schedule_dates = _schedule_dates(session, settings, start_date, end_date)
    if not schedule_dates:
        return AdminRuntimeResponse(
            text="В ближайшие дни расписания пока нет.",
            buttons=(_admin_menu_button(),),
        )
    return AdminRuntimeResponse(
        text="Даты расписания",
        buttons=tuple(_schedule_date_button(value) for value in schedule_dates)
        + (_admin_menu_button(),),
    )


def handle_admin_schedule_date_view(
    session: Session,
    settings: Settings,
    *,
    telegram_user_id: int | None,
    selected_date: date,
) -> AdminRuntimeResponse:
    require_admin_user(telegram_user_id, settings)
    bookings = _bookings_for_date(session, settings, selected_date)
    slots = _slots_for_date(session, settings, selected_date)
    lines = [
        f"Расписание: {_format_date_label(selected_date)}",
        f"Слотов: {len(slots)}",
        f"Открытых слотов: {sum(1 for slot in slots if not slot.is_blocked)}",
        f"Записей: {len(bookings)}",
        "",
        f"Открыть час: /open {selected_date.isoformat()} HH:MM",
        f"Открыть день: /open_day {selected_date.isoformat()} 10:00 20:00",
        f"Закрыть час: /close {selected_date.isoformat()} HH:MM",
        f"Закрыть остаток дня: /close_day {selected_date.isoformat()} HH:MM",
    ]
    buttons: list[AdminRuntimeButton] = []
    if bookings:
        lines.append("")
        lines.append("Записи:")
        for booking in bookings:
            lines.append(_booking_line(booking, settings))
            buttons.append(_booking_detail_button(booking, settings))
    else:
        lines.append("")
        lines.append(NO_BOOKINGS_TEXT)
    buttons.extend((_schedule_dates_button(), _admin_menu_button()))
    return AdminRuntimeResponse(text="\n".join(lines), buttons=tuple(buttons))


def handle_admin_booking_detail_view(
    session: Session,
    settings: Settings,
    *,
    telegram_user_id: int | None,
    booking_id: int,
) -> AdminRuntimeResponse:
    require_admin_user(telegram_user_id, settings)
    booking = session.get(Booking, booking_id)
    if booking is None:
        return AdminRuntimeResponse(
            text=BOOKING_NOT_FOUND_TEXT,
            buttons=(_schedule_dates_button(),),
        )
    client = booking.client
    contact_url = _client_contact_url(client) if client else None
    lines = [
        f"Запись #{booking.id}",
        _booking_line(booking, settings),
        f"Клиент: {_html(_client_display_name(client)) if client else 'неизвестно'}",
    ]
    if contact_url:
        lines.append(f'Чат: <a href="{escape(contact_url, quote=True)}">открыть</a>')
    lines.extend(
        [
            f"Адрес: {_html(booking.place)}",
            f"Цена: {booking.price_amount} GEL",
            f"Длительность: {booking.duration_minutes} мин",
        ]
    )
    buttons: list[AdminRuntimeButton] = []
    if contact_url:
        buttons.append(AdminRuntimeButton(label="Открыть чат", url=contact_url))
    buttons.extend(
        (
            AdminRuntimeButton(
                label="Перенести",
                callback_data=admin_callback_data(
                    AdminMenuAction.RESCHEDULE_DATE,
                    booking.id,
                ),
            ),
            AdminRuntimeButton(
                label="Отменить",
                callback_data=admin_callback_data(
                    AdminMenuAction.CANCEL_BOOKING,
                    booking.id,
                ),
            ),
        )
    )
    if client:
        buttons.append(
            AdminRuntimeButton(
                label="Карточка клиента",
                callback_data=admin_callback_data(
                    AdminMenuAction.CLIENT_CARD,
                    client.id,
                ),
            )
        )
    buttons.extend((_schedule_date_button(_booking_local_date(booking, settings)),))
    return AdminRuntimeResponse(text="\n".join(lines), buttons=tuple(buttons))


def handle_admin_reschedule_date_start(
    session: Session,
    settings: Settings,
    *,
    telegram_user_id: int | None,
    booking_id: int,
    now: datetime | None = None,
) -> AdminRuntimeResponse:
    require_admin_user(telegram_user_id, settings)
    booking = session.get(Booking, booking_id)
    if booking is None:
        return AdminRuntimeResponse(text=BOOKING_NOT_FOUND_TEXT)
    slots = tuple(list_available_slots(session, now=now))
    if not slots:
        return AdminRuntimeResponse(
            text=NO_AVAILABLE_SLOTS_TEXT,
            buttons=(_booking_detail_button(booking, settings),),
        )
    dates = sorted({_slot_local_date(slot, settings) for slot in slots})
    return AdminRuntimeResponse(
        text=f"Выберите новую дату для записи #{booking.id}",
        buttons=tuple(
            AdminRuntimeButton(
                label=_format_date_label(value),
                callback_data=admin_callback_data(
                    AdminMenuAction.RESCHEDULE_DATE,
                    f"{booking.id}|{value.isoformat()}",
                ),
            )
            for value in dates
        )
        + (_booking_detail_button(booking, settings),),
    )


def handle_admin_reschedule_date_view(
    session: Session,
    settings: Settings,
    *,
    telegram_user_id: int | None,
    booking_id: int,
    selected_date: date,
    now: datetime | None = None,
) -> AdminRuntimeResponse:
    require_admin_user(telegram_user_id, settings)
    booking = session.get(Booking, booking_id)
    if booking is None:
        return AdminRuntimeResponse(text=BOOKING_NOT_FOUND_TEXT)
    slots = tuple(
        slot
        for slot in list_available_slots(session, now=now)
        if _slot_local_date(slot, settings) == selected_date
    )
    if not slots:
        return AdminRuntimeResponse(
            text=NO_AVAILABLE_SLOTS_TEXT,
            buttons=(
                AdminRuntimeButton(
                    label="Назад к датам",
                    callback_data=admin_callback_data(
                        AdminMenuAction.RESCHEDULE_DATE,
                        booking.id,
                    ),
                ),
            ),
        )
    return AdminRuntimeResponse(
        text=f"Выберите новое время для записи #{booking.id}",
        buttons=tuple(
            AdminRuntimeButton(
                label=_slot_local_start(slot, settings).strftime("%H:%M"),
                callback_data=admin_callback_data(
                    AdminMenuAction.RESCHEDULE_SLOT,
                    f"{booking.id}|{slot.id}",
                ),
            )
            for slot in slots
        )
        + (
            AdminRuntimeButton(
                label="Назад к датам",
                callback_data=admin_callback_data(
                    AdminMenuAction.RESCHEDULE_DATE,
                    booking.id,
                ),
            ),
        ),
    )


def handle_admin_reschedule_confirm_prompt(
    session: Session,
    settings: Settings,
    *,
    telegram_user_id: int | None,
    booking_id: int,
    slot_id: int,
) -> AdminRuntimeResponse:
    require_admin_user(telegram_user_id, settings)
    booking = session.get(Booking, booking_id)
    slot = session.get(Slot, slot_id)
    if booking is None or slot is None:
        return AdminRuntimeResponse(text=BOOKING_NOT_FOUND_TEXT)
    return AdminRuntimeResponse(
        text="\n".join(
            [
                f"Перенести запись #{booking.id}?",
                f"Сейчас: {_booking_line(booking, settings)}",
                f"Новое время: {_format_datetime(_slot_local_start(slot, settings))}",
            ]
        ),
        buttons=(
            AdminRuntimeButton(
                label="Подтвердить перенос",
                callback_data=admin_callback_data(
                    AdminMenuAction.CONFIRM_RESCHEDULE,
                    f"{booking.id}|{slot.id}",
                ),
            ),
            _booking_detail_button(booking, settings),
        ),
    )


def handle_admin_cancel_confirm_prompt(
    session: Session,
    settings: Settings,
    *,
    telegram_user_id: int | None,
    booking_id: int,
) -> AdminRuntimeResponse:
    require_admin_user(telegram_user_id, settings)
    booking = session.get(Booking, booking_id)
    if booking is None:
        return AdminRuntimeResponse(text=BOOKING_NOT_FOUND_TEXT)
    return AdminRuntimeResponse(
        text="Точно отменить эту запись?\n" + _booking_line(booking, settings),
        buttons=(
            AdminRuntimeButton(
                label="Подтвердить отмену",
                callback_data=admin_callback_data(
                    AdminMenuAction.CONFIRM_CANCEL,
                    booking.id,
                ),
            ),
            _booking_detail_button(booking, settings),
        ),
    )


def build_admin_router(
    settings: Settings,
    *,
    async_session_factory: Callable[
        [],
        AbstractAsyncContextManager[AsyncSession],
    ]
    | None = None,
):
    """Build the aiogram router with all admin entrypoints behind the allowlist."""

    try:
        from aiogram import F, Router
        from aiogram.filters import Command
        from aiogram.types import (
            CallbackQuery,
            InlineKeyboardButton,
            InlineKeyboardMarkup,
            Message,
        )
    except ImportError as exc:  # pragma: no cover - exercised only without deps
        raise RuntimeError(
            "aiogram is required to build admin handlers; install requirements.txt"
        ) from exc

    router = Router(name="admin")

    @router.message(Command("admin"))
    async def admin_menu(message: Message) -> None:
        telegram_user_id = message.from_user.id if message.from_user else None
        if async_session_factory is not None:
            async with async_session_factory() as async_session:
                try:
                    response = await async_session.run_sync(
                        lambda session: handle_admin_dashboard(
                            session,
                            settings,
                            telegram_user_id=telegram_user_id,
                        )
                    )
                except AdminAccessDenied:
                    await async_session.rollback()
                    await message.answer(ADMIN_ACCESS_DENIED_TEXT)
                    return
                await async_session.rollback()

            await message.answer(
                response.text,
                reply_markup=_runtime_keyboard(response.buttons),
                parse_mode="HTML",
            )
            return

        try:
            response = handle_admin_menu_command(telegram_user_id, settings)
        except AdminAccessDenied:
            await message.answer(ADMIN_ACCESS_DENIED_TEXT)
            return

        await message.answer(
            response.text,
            reply_markup=_to_inline_keyboard(response.buttons),
            parse_mode="HTML",
        )

    @router.message(Command("book"))
    async def manual_booking(message: Message) -> None:
        telegram_user_id = message.from_user.id if message.from_user else None
        if async_session_factory is None:
            await message.answer(MANUAL_BOOKING_HELP_TEXT)
            return

        async with async_session_factory() as async_session:
            try:
                attempt = await async_session.run_sync(
                    lambda session: handle_admin_manual_booking_command(
                        session,
                        settings,
                        telegram_user_id=telegram_user_id,
                        command_text=message.text,
                    )
                )
            except AdminAccessDenied:
                await async_session.rollback()
                await message.answer(ADMIN_ACCESS_DENIED_TEXT)
                return
            except (BookingServiceError, SlotUnavailableError, ValueError) as exc:
                await async_session.rollback()
                await message.answer(
                    f"{_html(exc)}\n\n{MANUAL_BOOKING_HELP_TEXT}",
                    parse_mode="HTML",
                )
                return

            await _send_and_log_admin_notification(async_session, message.bot, attempt)
            await async_session.commit()

        await message.answer(
            attempt.response.text,
            reply_markup=_runtime_keyboard(attempt.response.buttons),
            parse_mode="HTML",
        )

    @router.message(Command("close"))
    async def close_slot(message: Message) -> None:
        await _handle_slot_schedule_message(
            message,
            lambda session: handle_admin_close_slot_command(
                session,
                settings,
                telegram_user_id=message.from_user.id if message.from_user else None,
                command_text=message.text,
            ),
        )

    @router.message(Command("close_day"))
    async def close_day(message: Message) -> None:
        await _handle_slot_schedule_message(
            message,
            lambda session: handle_admin_close_day_command(
                session,
                settings,
                telegram_user_id=message.from_user.id if message.from_user else None,
                command_text=message.text,
            ),
        )

    @router.message(Command("open"))
    async def open_slot(message: Message) -> None:
        await _handle_slot_schedule_message(
            message,
            lambda session: handle_admin_open_slot_command(
                session,
                settings,
                telegram_user_id=message.from_user.id if message.from_user else None,
                command_text=message.text,
            ),
        )

    @router.message(Command("open_day"))
    async def open_day(message: Message) -> None:
        await _handle_slot_schedule_message(
            message,
            lambda session: handle_admin_open_day_command(
                session,
                settings,
                telegram_user_id=message.from_user.id if message.from_user else None,
                command_text=message.text,
            ),
        )

    @router.callback_query(F.data.startswith(f"{ADMIN_CALLBACK_PREFIX}:"))
    async def admin_callback(callback: CallbackQuery) -> None:
        telegram_user_id = callback.from_user.id if callback.from_user else None
        try:
            response = await dispatch_admin_callback_payload(
                callback.data,
                settings,
                telegram_user_id=telegram_user_id,
                async_session_factory=async_session_factory,
                bot=callback.bot,
            )
        except AdminAccessDenied:
            await callback.answer(ADMIN_ACCESS_DENIED_TEXT, show_alert=True)
            return
        except ValueError:
            await callback.answer(UNKNOWN_ADMIN_ACTION_TEXT, show_alert=True)
            return

        await callback.answer()
        if callback.message:
            await callback.message.answer(
                response.text,
                reply_markup=_runtime_keyboard(response.buttons),
                parse_mode="HTML",
            )

    async def _handle_slot_schedule_message(
        message: Message,
        handler: Callable[[Session], AdminRuntimeResponse],
    ) -> None:
        if async_session_factory is None:
            await message.answer(SLOT_SCHEDULE_HELP_TEXT)
            return

        async with async_session_factory() as async_session:
            try:
                response = await async_session.run_sync(handler)
            except AdminAccessDenied:
                await async_session.rollback()
                await message.answer(ADMIN_ACCESS_DENIED_TEXT)
                return
            except ValueError as exc:
                await async_session.rollback()
                await message.answer(
                    f"{_html(exc)}\n\n{SLOT_SCHEDULE_HELP_TEXT}",
                    parse_mode="HTML",
                )
                return
            await async_session.commit()

        await message.answer(
            response.text,
            reply_markup=_runtime_keyboard(response.buttons),
            parse_mode="HTML",
        )

    def _to_inline_keyboard(buttons: tuple[MenuButton, ...]) -> InlineKeyboardMarkup:
        return InlineKeyboardMarkup(
            inline_keyboard=[
                [
                    InlineKeyboardButton(
                        text=button.label,
                        callback_data=admin_callback_data(button.action),
                    )
                ]
                for button in buttons
            ]
        )

    def _runtime_keyboard(
        buttons: tuple[AdminRuntimeButton, ...],
    ) -> InlineKeyboardMarkup | None:
        if not buttons:
            return None
        return InlineKeyboardMarkup(
            inline_keyboard=[
                [
                    InlineKeyboardButton(
                        text=button.label,
                        callback_data=button.callback_data,
                        url=button.url,
                    )
                ]
                for button in buttons
            ]
        )

    return router


async def dispatch_admin_callback_payload(
    payload: str | None,
    settings: Settings,
    *,
    telegram_user_id: int | None,
    async_session_factory: Callable[
        [],
        AbstractAsyncContextManager[AsyncSession],
    ]
    | None = None,
    bot: object | None = None,
) -> AdminRuntimeResponse:
    action, value = _parse_admin_runtime_payload(payload)
    if action is AdminMenuAction.TODAY:
        selected_date = datetime.now(settings.timezone_info).date()
        if async_session_factory is not None:
            async with async_session_factory() as async_session:
                return await async_session.run_sync(
                    lambda session: handle_admin_schedule_date_view(
                        session,
                        settings,
                        telegram_user_id=telegram_user_id,
                        selected_date=selected_date,
                    )
                )
    if action is AdminMenuAction.THIS_WEEK:
        start_date = datetime.now(settings.timezone_info).date()
        if async_session_factory is not None:
            async with async_session_factory() as async_session:
                return await async_session.run_sync(
                    lambda session: handle_admin_schedule_dates(
                        session,
                        settings,
                        telegram_user_id=telegram_user_id,
                        start_date=start_date,
                    )
                )
    if async_session_factory is not None and action is AdminMenuAction.CLOSE_SLOTS:
        start_date = datetime.now(settings.timezone_info).date()
        async with async_session_factory() as async_session:
            return await async_session.run_sync(
                lambda session: handle_admin_working_time_dates(
                    session,
                    settings,
                    telegram_user_id=telegram_user_id,
                    start_date=start_date,
                )
            )
    if (
        async_session_factory is not None
        and action is AdminMenuAction.WORKING_TIME_DATE
    ):
        selected_date = _parse_date_value(value)
        async with async_session_factory() as async_session:
            return await async_session.run_sync(
                lambda session: handle_admin_working_time_date_view(
                    session,
                    settings,
                    telegram_user_id=telegram_user_id,
                    selected_date=selected_date,
                )
            )
    if (
        async_session_factory is not None
        and action is AdminMenuAction.WORKING_TIME_CONFIRM
    ):
        async with async_session_factory() as async_session:
            return await async_session.run_sync(
                lambda session: handle_admin_working_time_confirm_prompt(
                    session,
                    settings,
                    telegram_user_id=telegram_user_id,
                    value=value,
                )
            )
    if (
        async_session_factory is not None
        and action is AdminMenuAction.WORKING_TIME_APPLY
    ):
        async with async_session_factory() as async_session:
            response = await async_session.run_sync(
                lambda session: handle_admin_working_time_apply(
                    session,
                    settings,
                    telegram_user_id=telegram_user_id,
                    value=value,
                )
            )
            await async_session.commit()
            return response
    if async_session_factory is not None and action is AdminMenuAction.SCHEDULE_DATE:
        selected_date = _parse_date_value(value)
        async with async_session_factory() as async_session:
            return await async_session.run_sync(
                lambda session: handle_admin_schedule_date_view(
                    session,
                    settings,
                    telegram_user_id=telegram_user_id,
                    selected_date=selected_date,
                )
            )
    if async_session_factory is not None and action is AdminMenuAction.BOOKING_DETAIL:
        booking_id = _parse_int_value(value)
        async with async_session_factory() as async_session:
            return await async_session.run_sync(
                lambda session: handle_admin_booking_detail_view(
                    session,
                    settings,
                    telegram_user_id=telegram_user_id,
                    booking_id=booking_id,
                )
            )
    if async_session_factory is not None and action is AdminMenuAction.CLIENTS:
        async with async_session_factory() as async_session:
            return await async_session.run_sync(
                lambda session: handle_admin_clients_list(
                    session,
                    settings,
                    telegram_user_id=telegram_user_id,
                )
            )
    if async_session_factory is not None and action is AdminMenuAction.CLIENT_CARD:
        client_id = _parse_int_value(value)
        async with async_session_factory() as async_session:
            return await async_session.run_sync(
                lambda session: handle_admin_client_card_view(
                    session,
                    settings,
                    telegram_user_id=telegram_user_id,
                    client_id=client_id,
                )
            )
    if async_session_factory is not None and action is AdminMenuAction.REFERRAL_BONUSES:
        async with async_session_factory() as async_session:
            return await async_session.run_sync(
                lambda session: handle_admin_referral_bonuses(
                    session,
                    settings,
                    telegram_user_id=telegram_user_id,
                )
            )
    if (
        async_session_factory is not None
        and action is AdminMenuAction.MARK_REFERRAL_BONUS_AWARDED
    ):
        bonus_id = _parse_int_value(value)
        async with async_session_factory() as async_session:
            response = await async_session.run_sync(
                lambda session: handle_admin_mark_referral_bonus_awarded(
                    session,
                    settings,
                    telegram_user_id=telegram_user_id,
                    bonus_id=bonus_id,
                )
            )
            await async_session.commit()
            return response
    if async_session_factory is not None and action is AdminMenuAction.REVENUE:
        async with async_session_factory() as async_session:
            return await async_session.run_sync(
                lambda session: handle_admin_metrics_dashboard(
                    session,
                    settings,
                    telegram_user_id=telegram_user_id,
                )
            )
    if action is AdminMenuAction.MANUAL_BOOKING:
        require_admin_user(telegram_user_id, settings)
        return AdminRuntimeResponse(
            text=MANUAL_BOOKING_HELP_TEXT,
            buttons=(_admin_menu_button(),),
        )
    if action is AdminMenuAction.CLOSE_SLOTS:
        require_admin_user(telegram_user_id, settings)
        return AdminRuntimeResponse(
            text=SLOT_SCHEDULE_HELP_TEXT,
            buttons=(_admin_menu_button(),),
        )
    if async_session_factory is not None and action is AdminMenuAction.RESCHEDULE_DATE:
        booking_id, selected_date = _parse_booking_date_value(value)
        async with async_session_factory() as async_session:
            if selected_date is None:
                return await async_session.run_sync(
                    lambda session: handle_admin_reschedule_date_start(
                        session,
                        settings,
                        telegram_user_id=telegram_user_id,
                        booking_id=booking_id,
                    )
                )
            return await async_session.run_sync(
                lambda session: handle_admin_reschedule_date_view(
                    session,
                    settings,
                    telegram_user_id=telegram_user_id,
                    booking_id=booking_id,
                    selected_date=selected_date,
                )
            )
    if async_session_factory is not None and action is AdminMenuAction.RESCHEDULE_SLOT:
        booking_id, slot_id = _parse_two_ints(value)
        async with async_session_factory() as async_session:
            return await async_session.run_sync(
                lambda session: handle_admin_reschedule_confirm_prompt(
                    session,
                    settings,
                    telegram_user_id=telegram_user_id,
                    booking_id=booking_id,
                    slot_id=slot_id,
                )
            )
    if (
        async_session_factory is not None
        and action is AdminMenuAction.CANCEL_BOOKING
        and value
    ):
        booking_id = _parse_int_value(value)
        async with async_session_factory() as async_session:
            return await async_session.run_sync(
                lambda session: handle_admin_cancel_confirm_prompt(
                    session,
                    settings,
                    telegram_user_id=telegram_user_id,
                    booking_id=booking_id,
                )
            )
    if (
        async_session_factory is not None
        and action is AdminMenuAction.CONFIRM_RESCHEDULE
    ):
        booking_id, slot_id = _parse_two_ints(value)
        async with async_session_factory() as async_session:
            attempt = await async_session.run_sync(
                lambda session: _commit_admin_reschedule(
                    session,
                    settings,
                    telegram_user_id=telegram_user_id,
                    booking_id=booking_id,
                    slot_id=slot_id,
                )
            )
            await _send_and_log_admin_notification(async_session, bot, attempt)
            await async_session.commit()
            return attempt.response
    if async_session_factory is not None and action is AdminMenuAction.CONFIRM_CANCEL:
        booking_id = _parse_int_value(value)
        async with async_session_factory() as async_session:
            attempt = await async_session.run_sync(
                lambda session: _commit_admin_cancel(
                    session,
                    settings,
                    telegram_user_id=telegram_user_id,
                    booking_id=booking_id,
                )
            )
            await _send_and_log_admin_notification(async_session, bot, attempt)
            await async_session.commit()
            return attempt.response
    if action is AdminMenuAction.MENU:
        if async_session_factory is not None:
            async with async_session_factory() as async_session:
                return await async_session.run_sync(
                    lambda session: handle_admin_dashboard(
                        session,
                        settings,
                        telegram_user_id=telegram_user_id,
                    )
                )
        menu = handle_admin_menu_command(telegram_user_id, settings)
        return AdminRuntimeResponse(
            text=menu.text,
            buttons=tuple(
                AdminRuntimeButton(
                    label=button.label,
                    callback_data=button.callback_data,
                )
                for button in menu.buttons
            ),
        )

    response = handle_admin_callback(telegram_user_id, settings, payload)
    return AdminRuntimeResponse(text=response.text)


def _settings_location_links(settings: Settings) -> dict[str, str | None]:
    return {
        "yandex_map_url": settings.yandex_map_url,
        "google_map_url": settings.google_map_url,
        "default_map_url": settings.default_map_url,
    }


def _parse_manual_booking_command(
    command_text: str | None,
    settings: Settings,
) -> ManualBookingCommand:
    parts = (command_text or "").strip().split(maxsplit=6)
    if len(parts) != 7 or not _command_matches(parts[0], "/book"):
        raise ValueError("Неверный формат команды.")

    try:
        selected_date = date.fromisoformat(parts[2])
        hour, minute = (int(value) for value in parts[3].split(":", maxsplit=1))
        starts_at = datetime(
            selected_date.year,
            selected_date.month,
            selected_date.day,
            hour,
            minute,
        )
        duration_minutes = int(parts[4])
        price_amount = Decimal(parts[5].replace(",", "."))
    except (ArithmeticError, TypeError, ValueError) as exc:
        raise ValueError(
            "Не удалось разобрать дату, время, длительность или цену."
        ) from exc

    client_ref = parts[1].strip()
    if not client_ref:
        raise ValueError("Укажите client_id или username.")
    service = parts[6].strip()
    if not service:
        raise ValueError("Укажите услугу.")
    if duration_minutes <= 0:
        raise ValueError("Длительность должна быть больше 0 минут.")
    if price_amount < 0:
        raise ValueError("Цена не может быть отрицательной.")

    now_local = datetime.now(settings.timezone_info).replace(tzinfo=None)
    if starts_at <= now_local:
        raise ValueError("Нельзя создать запись в прошлом.")

    return ManualBookingCommand(
        client_ref=client_ref,
        starts_at=starts_at,
        duration_minutes=duration_minutes,
        price_amount=price_amount,
        service=service,
    )


def _resolve_client_reference(session: Session, client_ref: str) -> Client:
    normalized_ref = client_ref.strip()
    if not normalized_ref:
        raise BookingServiceError("Client reference is required")

    if normalized_ref.isdigit():
        client = session.get(Client, int(normalized_ref))
        if client is not None:
            return client
        raise BookingServiceError(f"Client not found: {normalized_ref}")

    username = _normalize_username_reference(normalized_ref)
    if not username:
        raise BookingServiceError(f"Client not found: {client_ref}")

    client = session.scalar(
        select(Client)
        .join(User, isouter=True)
        .where(func.lower(User.username) == username.lower())
        .limit(1)
    )
    if client is None:
        raise BookingServiceError(f"Client not found: {client_ref}")
    return client


def _get_or_create_manual_slot(
    session: Session,
    settings: Settings,
    *,
    starts_at: datetime,
) -> Slot:
    slot = session.scalar(
        select(Slot).where(
            Slot.starts_at == starts_at,
            Slot.place == settings.default_place,
        )
    )
    if slot is not None:
        return slot

    slot = Slot(
        starts_at=starts_at,
        ends_at=starts_at + timedelta(hours=1),
        place=settings.default_place,
        is_blocked=False,
    )
    session.add(slot)
    session.flush()
    return slot


def _parse_slot_closing_command(
    command_text: str | None,
    settings: Settings,
    command_name: str,
) -> datetime:
    parts = (command_text or "").strip().split(maxsplit=2)
    if len(parts) != 3 or not _command_matches(parts[0], command_name):
        raise ValueError("Неверный формат команды.")

    try:
        selected_date = date.fromisoformat(parts[1])
        hour, minute = (int(value) for value in parts[2].split(":", maxsplit=1))
        starts_at = datetime(
            selected_date.year,
            selected_date.month,
            selected_date.day,
            hour,
            minute,
        )
    except (TypeError, ValueError) as exc:
        raise ValueError("Не удалось разобрать дату или время.") from exc

    now_local = datetime.now(settings.timezone_info).replace(tzinfo=None)
    if starts_at <= now_local:
        raise ValueError("Нельзя закрыть слот в прошлом.")
    return starts_at


def _parse_slot_opening_command(
    command_text: str | None,
    settings: Settings,
    command_name: str,
) -> datetime:
    parts = (command_text or "").strip().split(maxsplit=2)
    if len(parts) != 3 or not _command_matches(parts[0], command_name):
        raise ValueError("Неверный формат команды.")

    starts_at = _parse_local_datetime(parts[1], parts[2])
    now_local = datetime.now(settings.timezone_info).replace(tzinfo=None)
    if starts_at <= now_local:
        raise ValueError("Нельзя открыть слот в прошлом.")
    return starts_at


def _parse_slot_opening_day_command(
    command_text: str | None,
    settings: Settings,
    command_name: str,
) -> tuple[datetime, datetime]:
    parts = (command_text or "").strip().split(maxsplit=3)
    if len(parts) != 4 or not _command_matches(parts[0], command_name):
        raise ValueError("Неверный формат команды.")

    starts_at = _parse_local_datetime(parts[1], parts[2])
    ends_at = _parse_local_datetime(parts[1], parts[3])
    now_local = datetime.now(settings.timezone_info).replace(tzinfo=None)
    if starts_at <= now_local:
        raise ValueError("Нельзя открыть рабочий день в прошлом.")
    if ends_at <= starts_at:
        raise ValueError("Время окончания должно быть позже начала.")
    return starts_at, ends_at


def _parse_local_datetime(raw_date: str, raw_time: str) -> datetime:
    try:
        selected_date = date.fromisoformat(raw_date)
        hour, minute = (int(value) for value in raw_time.split(":", maxsplit=1))
        return datetime(
            selected_date.year,
            selected_date.month,
            selected_date.day,
            hour,
            minute,
        )
    except (TypeError, ValueError) as exc:
        raise ValueError("Не удалось разобрать дату или время.") from exc


def _find_slot_by_local_start(
    session: Session,
    settings: Settings,
    *,
    starts_at: datetime,
) -> Slot | None:
    selected_date = starts_at.date()
    selected_time = starts_at.time()
    for slot in _slots_for_date(session, settings, selected_date):
        if _slot_local_start(slot, settings).time() == selected_time:
            return slot
    return None


def _active_booking_for_slot(session: Session, slot: Slot) -> Booking | None:
    return session.scalar(
        select(Booking)
        .where(
            Booking.status.in_(ACTIVE_BOOKING_STATUSES),
            Booking.starts_at < slot.ends_at,
            Booking.ends_at > slot.starts_at,
        )
        .order_by(Booking.starts_at)
        .limit(1)
    )


def _block_slot(slot: Slot, *, note: str) -> None:
    slot.is_blocked = True
    slot.note = note


def _open_slot(
    session: Session,
    settings: Settings,
    *,
    starts_at: datetime,
    note: str,
) -> tuple[Slot, str]:
    slot = _find_slot_by_local_start(session, settings, starts_at=starts_at)
    if slot is None:
        slot = Slot(
            starts_at=starts_at,
            ends_at=starts_at + timedelta(hours=1),
            place=settings.default_place,
            is_blocked=False,
            note=note,
        )
        session.add(slot)
        session.flush()
        return slot, "created"

    if slot.is_blocked:
        slot.is_blocked = False
        slot.note = note
        return slot, "reopened"

    return slot, "already_open"


def _command_matches(raw_command: str, expected_command: str) -> bool:
    return raw_command.split("@", maxsplit=1)[0] == expected_command


def _normalize_username_reference(client_ref: str) -> str | None:
    value = client_ref.strip()
    if value.startswith("https://t.me/"):
        value = value.removeprefix("https://t.me/")
    elif value.startswith("http://t.me/"):
        value = value.removeprefix("http://t.me/")
    elif value.startswith("t.me/"):
        value = value.removeprefix("t.me/")
    if value.startswith("@"):
        value = value[1:]
    value = value.split("/", maxsplit=1)[0].strip()
    return value or None


def _working_time_date_label(
    session: Session,
    settings: Settings,
    selected_date: date,
) -> str:
    slots = _slots_for_date(session, settings, selected_date)
    active_count = sum(
        1
        for booking in _bookings_for_date(session, settings, selected_date)
        if booking.status in ADMIN_ACTIVE_BOOKING_STATUSES
    )
    if not slots and not active_count:
        return f"{_format_date_label(selected_date)} · нет слотов"
    open_count = sum(1 for slot in slots if not slot.is_blocked)
    blocked_count = sum(1 for slot in slots if slot.is_blocked)
    return (
        f"{_format_date_label(selected_date)} · "
        f"{open_count} откр / {blocked_count} закр / {active_count} зап"
    )


def _working_time_date_button(
    value: date,
    *,
    label: str | None = None,
) -> AdminRuntimeButton:
    return AdminRuntimeButton(
        label=label or _format_date_label(value),
        callback_data=admin_callback_data(
            AdminMenuAction.WORKING_TIME_DATE,
            value.isoformat(),
        ),
    )


def _working_time_dates_button() -> AdminRuntimeButton:
    return AdminRuntimeButton(
        label="Назад к датам",
        callback_data=admin_callback_data(AdminMenuAction.CLOSE_SLOTS),
    )


def _working_time_confirm_button(
    *,
    label: str,
    operation: str,
    selected_date: date,
    start_time: str,
    end_time: str | None = None,
) -> AdminRuntimeButton:
    return AdminRuntimeButton(
        label=label,
        callback_data=admin_callback_data(
            AdminMenuAction.WORKING_TIME_CONFIRM,
            _working_time_operation_value(
                WorkingTimeOperation(
                    operation=operation,
                    selected_date=selected_date,
                    start_time=start_time,
                    end_time=end_time,
                )
            ),
        ),
    )


def _working_time_hour_buttons(
    session: Session,
    settings: Settings,
    *,
    selected_date: date,
) -> tuple[AdminRuntimeButton, ...]:
    buttons: list[AdminRuntimeButton] = []
    for start_time in WORKING_HOUR_STARTS:
        if not _is_future_working_time(selected_date, start_time, settings):
            continue
        starts_at = _parse_local_datetime(selected_date.isoformat(), start_time)
        slot = _find_slot_by_local_start(session, settings, starts_at=starts_at)
        if slot is None:
            buttons.append(
                _working_time_confirm_button(
                    label=f"Открыть {start_time}",
                    operation=WORKING_OPEN_SLOT,
                    selected_date=selected_date,
                    start_time=start_time,
                )
            )
            continue

        booking = _active_booking_for_slot(session, slot)
        if booking is not None:
            buttons.append(
                AdminRuntimeButton(
                    label=f"{start_time} · запись #{booking.id}",
                    callback_data=admin_callback_data(
                        AdminMenuAction.BOOKING_DETAIL,
                        booking.id,
                    ),
                )
            )
            continue

        if slot.is_blocked:
            buttons.append(
                _working_time_confirm_button(
                    label=f"Открыть {start_time}",
                    operation=WORKING_OPEN_SLOT,
                    selected_date=selected_date,
                    start_time=start_time,
                )
            )
        else:
            buttons.append(
                _working_time_confirm_button(
                    label=f"Закрыть {start_time}",
                    operation=WORKING_CLOSE_SLOT,
                    selected_date=selected_date,
                    start_time=start_time,
                )
            )
    return tuple(buttons)


def _is_future_working_time(
    selected_date: date,
    start_time: str,
    settings: Settings,
) -> bool:
    starts_at = _parse_local_datetime(selected_date.isoformat(), start_time)
    now_local = datetime.now(settings.timezone_info).replace(tzinfo=None)
    return starts_at > now_local


def _working_time_operation_value(operation: WorkingTimeOperation) -> str:
    parts = [
        operation.operation,
        operation.selected_date.isoformat(),
        operation.start_time,
    ]
    if operation.end_time is not None:
        parts.append(operation.end_time)
    return "|".join(parts)


def _parse_working_time_operation(value: str | None) -> WorkingTimeOperation:
    if value is None:
        raise ValueError("Missing callback value")
    parts = value.split("|")
    if len(parts) not in (3, 4):
        raise ValueError("Invalid callback value")

    operation, raw_date, start_time = parts[:3]
    end_time = parts[3] if len(parts) == 4 else None
    if operation not in {
        WORKING_OPEN_DAY,
        WORKING_CLOSE_DAY,
        WORKING_OPEN_SLOT,
        WORKING_CLOSE_SLOT,
    }:
        raise ValueError("Invalid callback value")
    if operation == WORKING_OPEN_DAY and end_time is None:
        raise ValueError("Invalid callback value")
    if operation != WORKING_OPEN_DAY and end_time is not None:
        raise ValueError("Invalid callback value")

    try:
        selected_date = date.fromisoformat(raw_date)
    except ValueError as exc:
        raise ValueError("Invalid callback value") from exc
    _parse_local_datetime(raw_date, start_time)
    if end_time is not None:
        _parse_local_datetime(raw_date, end_time)
    return WorkingTimeOperation(
        operation=operation,
        selected_date=selected_date,
        start_time=start_time,
        end_time=end_time,
    )


def _working_time_operation_summary(operation: WorkingTimeOperation) -> str:
    formatted_date = _format_date_label(operation.selected_date)
    if operation.operation == WORKING_OPEN_DAY:
        return (
            f"Открыть рабочий день: {formatted_date} "
            f"{operation.start_time}-{operation.end_time}"
        )
    if operation.operation == WORKING_CLOSE_DAY:
        if operation.start_time == "00:00":
            return f"Закрыть свободные слоты за весь день: {formatted_date}"
        return f"Закрыть свободные слоты: {formatted_date} с {operation.start_time}"
    if operation.operation == WORKING_OPEN_SLOT:
        return f"Открыть час: {formatted_date} {operation.start_time}"
    if operation.operation == WORKING_CLOSE_SLOT:
        return f"Закрыть свободный час: {formatted_date} {operation.start_time}"
    raise ValueError("Invalid callback value")


def _working_time_command_text(operation: WorkingTimeOperation) -> str:
    selected_date = operation.selected_date.isoformat()
    if operation.operation == WORKING_OPEN_DAY:
        return f"/open_day {selected_date} {operation.start_time} {operation.end_time}"
    if operation.operation == WORKING_CLOSE_DAY:
        return f"/close_day {selected_date} {operation.start_time}"
    if operation.operation == WORKING_OPEN_SLOT:
        return f"/open {selected_date} {operation.start_time}"
    if operation.operation == WORKING_CLOSE_SLOT:
        return f"/close {selected_date} {operation.start_time}"
    raise ValueError("Invalid callback value")


def _parse_admin_runtime_payload(
    payload: str | None,
) -> tuple[AdminMenuAction, str | None]:
    if not isinstance(payload, str):
        raise ValueError("Missing admin callback payload")
    prefix, separator, remainder = payload.partition(":")
    if prefix != ADMIN_CALLBACK_PREFIX or not separator or not remainder:
        raise ValueError("Not an admin callback payload")
    raw_action, value_separator, raw_value = remainder.partition(":")
    try:
        action = AdminMenuAction(raw_action)
    except ValueError as exc:
        raise ValueError("Unknown admin action") from exc
    return action, raw_value if value_separator else None


def _parse_int_value(value: str | None) -> int:
    if value is None:
        raise ValueError("Missing callback value")
    try:
        return int(value)
    except ValueError as exc:
        raise ValueError("Invalid callback value") from exc


def _parse_date_value(value: str | None) -> date:
    if value is None:
        raise ValueError("Missing callback value")
    try:
        return date.fromisoformat(value)
    except ValueError as exc:
        raise ValueError("Invalid callback value") from exc


def _parse_booking_date_value(value: str | None) -> tuple[int, date | None]:
    if value is None:
        raise ValueError("Missing callback value")
    if "|" not in value:
        return _parse_int_value(value), None
    raw_booking_id, raw_date = value.split("|", maxsplit=1)
    return _parse_int_value(raw_booking_id), _parse_date_value(raw_date)


def _parse_two_ints(value: str | None) -> tuple[int, int]:
    if value is None or "|" not in value:
        raise ValueError("Invalid callback value")
    left, right = value.split("|", maxsplit=1)
    return _parse_int_value(left), _parse_int_value(right)


def _admin_dashboard_buttons() -> tuple[AdminRuntimeButton, ...]:
    return (
        AdminRuntimeButton(
            label="Записи",
            callback_data=admin_callback_data(AdminMenuAction.THIS_WEEK),
        ),
        AdminRuntimeButton(
            label="Клиенты",
            callback_data=admin_callback_data(AdminMenuAction.CLIENTS),
        ),
        AdminRuntimeButton(
            label="Метрики",
            callback_data=admin_callback_data(AdminMenuAction.REVENUE),
        ),
        AdminRuntimeButton(
            label="Создать запись",
            callback_data=admin_callback_data(AdminMenuAction.MANUAL_BOOKING),
        ),
        AdminRuntimeButton(
            label="Рабочее время",
            callback_data=admin_callback_data(AdminMenuAction.CLOSE_SLOTS),
        ),
        AdminRuntimeButton(
            label="Сегодня",
            callback_data=admin_callback_data(AdminMenuAction.TODAY),
        ),
        AdminRuntimeButton(
            label="Бонусы",
            callback_data=admin_callback_data(AdminMenuAction.REFERRAL_BONUSES),
        ),
    )


def _clients_button() -> AdminRuntimeButton:
    return AdminRuntimeButton(
        label="Назад к клиентам",
        callback_data=admin_callback_data(AdminMenuAction.CLIENTS),
    )


def _admin_menu_button() -> AdminRuntimeButton:
    return AdminRuntimeButton(
        label="Главная",
        callback_data=admin_callback_data(AdminMenuAction.MENU),
    )


def _schedule_dates_button() -> AdminRuntimeButton:
    return AdminRuntimeButton(
        label="Даты расписания",
        callback_data=admin_callback_data(AdminMenuAction.THIS_WEEK),
    )


def _schedule_date_button(value: date) -> AdminRuntimeButton:
    return AdminRuntimeButton(
        label=_format_date_label(value),
        callback_data=admin_callback_data(
            AdminMenuAction.SCHEDULE_DATE,
            value.isoformat(),
        ),
    )


def _booking_detail_button(booking: Booking, settings: Settings) -> AdminRuntimeButton:
    return AdminRuntimeButton(
        label=f"{_booking_local_start(booking, settings):%H:%M} #{booking.id}",
        callback_data=admin_callback_data(AdminMenuAction.BOOKING_DETAIL, booking.id),
    )


def _client_button_label(client: Client) -> str:
    return f"{_client_display_name(client)} #{client.id}"


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


def _client_bookings(
    session: Session,
    *,
    client_id: int,
    active: bool,
    now: datetime | None = None,
) -> tuple[Booking, ...]:
    cutoff = now or datetime.now(UTC)
    active_statuses = (BookingStatus.CONFIRMED, BookingStatus.RESCHEDULED)
    statement = select(Booking).where(Booking.client_id == client_id)
    if active:
        statement = statement.where(
            Booking.starts_at > cutoff,
            Booking.status.in_(active_statuses),
        ).order_by(Booking.starts_at)
    else:
        statement = statement.where(
            (Booking.starts_at <= cutoff) | Booking.status.not_in(active_statuses)
        ).order_by(Booking.starts_at.desc())
    return tuple(session.scalars(statement))


def _upcoming_bookings(
    session: Session,
    settings: Settings,
    *,
    now: datetime,
) -> tuple[Booking, ...]:
    cutoff = _datetime_local(now, settings)
    bookings = tuple(
        booking
        for booking in session.scalars(select(Booking).order_by(Booking.starts_at))
        if booking.status in ADMIN_ACTIVE_BOOKING_STATUSES
        and _booking_local_start(booking, settings) > cutoff
    )
    return tuple(
        sorted(
            bookings,
            key=lambda booking: _booking_local_start(booking, settings),
        )
    )


def _client_count(session: Session) -> int:
    return session.scalar(select(func.count(Client.id))) or 0


def _client_metric_cards(session: Session) -> tuple[ClientCard, ...]:
    clients = tuple(session.scalars(select(Client).order_by(Client.id)))
    cards = tuple(
        client_card_summary(session, client_id=client.id)
        for client in clients
        if client.id is not None
    )
    return tuple(
        sorted(
            cards,
            key=lambda card: (card.total_spent, card.visit_count, card.client_id),
            reverse=True,
        )
    )


def _bookings_for_date(
    session: Session,
    settings: Settings,
    selected_date: date,
) -> tuple[Booking, ...]:
    return tuple(
        booking
        for booking in session.scalars(select(Booking).order_by(Booking.starts_at))
        if _booking_local_date(booking, settings) == selected_date
    )


def _slots_for_date(
    session: Session,
    settings: Settings,
    selected_date: date,
) -> tuple[Slot, ...]:
    return tuple(
        slot
        for slot in session.scalars(select(Slot).order_by(Slot.starts_at))
        if _slot_local_date(slot, settings) == selected_date
    )


def _schedule_dates(
    session: Session,
    settings: Settings,
    start_date: date,
    end_date: date,
) -> tuple[date, ...]:
    dates = {
        _slot_local_date(slot, settings)
        for slot in session.scalars(select(Slot).order_by(Slot.starts_at))
        if start_date <= _slot_local_date(slot, settings) < end_date
    }
    dates.update(
        _booking_local_date(booking, settings)
        for booking in session.scalars(select(Booking).order_by(Booking.starts_at))
        if start_date <= _booking_local_date(booking, settings) < end_date
    )
    return tuple(sorted(dates))


def _week_start(value: datetime, settings: Settings) -> datetime:
    local_value = _datetime_local(value, settings)
    start = local_value - timedelta(days=local_value.weekday())
    return start.replace(hour=0, minute=0, second=0, microsecond=0)


def _booking_line(booking: Booking, settings: Settings) -> str:
    starts_at = _booking_local_start(booking, settings)
    client = booking.client
    client_label = "клиент неизвестен"
    if client is not None:
        contact_url = _client_contact_url(client)
        display_name = _client_display_name(client)
        client_label = _html(display_name)
        if contact_url:
            client_label = (
                f'<a href="{escape(contact_url, quote=True)}">{client_label}</a>'
            )
    return (
        f"- #{booking.id} {_format_datetime(starts_at)} "
        f"{_html(_service_label(booking.service))} / {_status_label(booking.status)}"
        f" / {client_label}"
    )


def _booking_local_date(booking: Booking, settings: Settings) -> date:
    return _booking_local_start(booking, settings).date()


def _booking_local_start(booking: Booking, settings: Settings) -> datetime:
    return _datetime_local(booking.starts_at, settings)


def _slot_local_date(slot: Slot, settings: Settings) -> date:
    return _slot_local_start(slot, settings).date()


def _slot_local_start(slot: Slot, settings: Settings) -> datetime:
    return _datetime_local(slot.starts_at, settings)


def _datetime_local(value: datetime, settings: Settings) -> datetime:
    if value.tzinfo is None:
        value = value.replace(tzinfo=settings.timezone_info)
    return value.astimezone(settings.timezone_info)


def _format_date_label(value: date) -> str:
    return (
        f"{_WEEKDAYS_SHORT_RU[value.weekday()]}, {value.day} {_MONTHS_RU[value.month]}"
    )


def _format_datetime(value: datetime) -> str:
    return (
        f"{value.day} {_MONTHS_RU[value.month]}, "
        f"{_WEEKDAYS_RU[value.weekday()]} {value:%H:%M}"
    )


def _format_money(value: Decimal) -> str:
    return f"{value:.2f}".rstrip("0").rstrip(".")


def _service_label(value: str) -> str:
    return haircut_service_label(value)


def _status_label(value: BookingStatus) -> str:
    return {
        BookingStatus.DRAFT: "черновик",
        BookingStatus.CONFIRMED: "подтверждена",
        BookingStatus.RESCHEDULED: "перенесена",
        BookingStatus.CANCELLED_BY_CLIENT: "отменена клиентом",
        BookingStatus.CANCELLED_BY_ADMIN: "отменена админом",
        BookingStatus.COMPLETED: "завершена",
        BookingStatus.NO_SHOW: "не пришел",
    }[value]


def _commit_admin_reschedule(
    session: Session,
    settings: Settings,
    *,
    telegram_user_id: int | None,
    booking_id: int,
    slot_id: int,
) -> AdminNotificationAttempt:
    require_admin_user(telegram_user_id, settings)
    booking = reschedule_booking(
        session,
        booking_id=booking_id,
        new_slot_id=slot_id,
        reason="admin moved booking from schedule view",
    )
    text = booking_rescheduled_message(
        booking,
        timezone=settings.timezone_info,
        **_settings_location_links(settings),
    )
    return AdminNotificationAttempt(
        response=AdminRuntimeResponse(
            text="Запись перенесена\n" + _booking_line(booking, settings),
            buttons=(
                _booking_detail_button(booking, settings),
                _schedule_date_button(_booking_local_date(booking, settings)),
            ),
        ),
        booking_id=booking.id,
        client_id=booking.client_id,
        recipient_telegram_id=_recipient_telegram_id(booking),
        kind="booking_rescheduled",
        text=text,
    )


def _commit_admin_cancel(
    session: Session,
    settings: Settings,
    *,
    telegram_user_id: int | None,
    booking_id: int,
) -> AdminNotificationAttempt:
    require_admin_user(telegram_user_id, settings)
    booking = cancel_booking_by_admin(
        session,
        booking_id=booking_id,
        reason="admin cancelled booking from schedule view",
    )
    text = booking_cancelled_message(
        booking,
        reason="cancelled by admin",
        timezone=settings.timezone_info,
        **_settings_location_links(settings),
    )
    return AdminNotificationAttempt(
        response=AdminRuntimeResponse(
            text="Запись отменена\n" + _booking_line(booking, settings),
            buttons=(
                _schedule_date_button(_booking_local_date(booking, settings)),
                _admin_menu_button(),
            ),
        ),
        booking_id=booking.id,
        client_id=booking.client_id,
        recipient_telegram_id=_recipient_telegram_id(booking),
        kind="booking_cancelled",
        text=text,
    )


async def _send_and_log_admin_notification(
    async_session: AsyncSession,
    bot,
    attempt: AdminNotificationAttempt,
) -> None:
    status = DeliveryStatus.PENDING
    error = None
    sent_at = None
    if attempt.recipient_telegram_id is None:
        status = DeliveryStatus.FAILED
        error = "Client has no Telegram identity"
    else:
        try:
            await bot.send_message(attempt.recipient_telegram_id, attempt.text)
        except Exception as exc:  # noqa: BLE001 - delivery failures must be logged
            status = DeliveryStatus.FAILED
            error = str(exc) or exc.__class__.__name__
        else:
            status = DeliveryStatus.SENT
            sent_at = datetime.now(UTC)

    await async_session.run_sync(
        lambda session: _record_admin_notification_log(
            session,
            attempt=attempt,
            status=status,
            error=error,
            sent_at=sent_at,
        )
    )


def _record_admin_notification_log(
    session: Session,
    *,
    attempt: AdminNotificationAttempt,
    status: DeliveryStatus,
    error: str | None,
    sent_at: datetime | None,
) -> None:
    session.add(
        NotificationLog(
            booking_id=attempt.booking_id,
            client_id=attempt.client_id,
            kind=attempt.kind,
            recipient_telegram_id=attempt.recipient_telegram_id,
            status=status,
            error=error,
            sent_at=sent_at,
        )
    )
    session.flush()


def _recipient_telegram_id(booking: Booking) -> int | None:
    user = booking.client.user if booking.client else None
    return user.telegram_id if user else None


def _html(value: object) -> str:
    return escape(str(value), quote=False)


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

_WEEKDAYS_SHORT_RU = (
    "Пн",
    "Вт",
    "Ср",
    "Чт",
    "Пт",
    "Сб",
    "Вс",
)
