"""Admin command and callback guards."""

from __future__ import annotations

from collections.abc import Callable
from contextlib import AbstractAsyncContextManager
from dataclasses import dataclass
from datetime import UTC, date, datetime, timedelta
from decimal import Decimal
from html import escape

from sqlalchemy import select
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
    Slot,
    User,
)
from app.services.booking import (
    cancel_booking_by_admin,
    create_manual_booking,
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

ADMIN_MENU_TEXT = "Админ-меню"
ADMIN_ACCESS_DENIED_TEXT = "Нет доступа к админке"
UNKNOWN_ADMIN_ACTION_TEXT = "Неизвестное действие"
NO_CLIENTS_TEXT = "Клиентов пока нет. Они появятся после первой записи через бота."
CLIENT_NOT_FOUND_TEXT = "Клиент не найден."
NO_BOOKINGS_TEXT = "На эту дату записей пока нет."
BOOKING_NOT_FOUND_TEXT = "Запись не найдена."
NO_AVAILABLE_SLOTS_TEXT = "Свободных слотов пока нет."


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
    buttons.extend((_clients_button(), _admin_menu_button()))
    return AdminRuntimeResponse(text="\n".join(lines), buttons=tuple(buttons))


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
        f"Записей: {len(bookings)}",
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

    @router.callback_query(F.data.startswith(f"{ADMIN_CALLBACK_PREFIX}:"))
    async def admin_callback(callback: CallbackQuery) -> None:
        telegram_user_id = callback.from_user.id if callback.from_user else None
        try:
            response = await _dispatch_admin_callback(
                callback.data,
                telegram_user_id,
                callback.bot,
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

    async def _dispatch_admin_callback(
        payload: str | None,
        telegram_user_id: int | None,
        bot,
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
        if (
            async_session_factory is not None
            and action is AdminMenuAction.SCHEDULE_DATE
        ):
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
        if (
            async_session_factory is not None
            and action is AdminMenuAction.BOOKING_DETAIL
        ):
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
        if (
            async_session_factory is not None
            and action is AdminMenuAction.RESCHEDULE_DATE
        ):
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
        if (
            async_session_factory is not None
            and action is AdminMenuAction.RESCHEDULE_SLOT
        ):
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
        if (
            async_session_factory is not None
            and action is AdminMenuAction.CONFIRM_CANCEL
        ):
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


def _settings_location_links(settings: Settings) -> dict[str, str | None]:
    return {
        "yandex_map_url": settings.yandex_map_url,
        "google_map_url": settings.google_map_url,
        "default_map_url": settings.default_map_url,
    }


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


def _clients_button() -> AdminRuntimeButton:
    return AdminRuntimeButton(
        label="Назад к клиентам",
        callback_data=admin_callback_data(AdminMenuAction.CLIENTS),
    )


def _admin_menu_button() -> AdminRuntimeButton:
    return AdminRuntimeButton(
        label="Админ-меню",
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


def _booking_line(booking: Booking, settings: Settings) -> str:
    starts_at = _booking_local_start(booking, settings)
    return (
        f"- #{booking.id} {_format_datetime(starts_at)} "
        f"{_html(_service_label(booking.service))} / {_status_label(booking.status)}"
    )


def _booking_local_date(booking: Booking, settings: Settings) -> date:
    return _booking_local_start(booking, settings).date()


def _booking_local_start(booking: Booking, settings: Settings) -> datetime:
    starts_at = booking.starts_at
    if starts_at.tzinfo is None:
        starts_at = starts_at.replace(tzinfo=settings.timezone_info)
    return starts_at.astimezone(settings.timezone_info)


def _slot_local_date(slot: Slot, settings: Settings) -> date:
    return _slot_local_start(slot, settings).date()


def _slot_local_start(slot: Slot, settings: Settings) -> datetime:
    starts_at = slot.starts_at
    if starts_at.tzinfo is None:
        starts_at = starts_at.replace(tzinfo=settings.timezone_info)
    return starts_at.astimezone(settings.timezone_info)


def _format_date_label(value: date) -> str:
    return (
        f"{_WEEKDAYS_SHORT_RU[value.weekday()]}, {value.day} {_MONTHS_RU[value.month]}"
    )


def _format_datetime(value: datetime) -> str:
    return (
        f"{value.day} {_MONTHS_RU[value.month]}, "
        f"{_WEEKDAYS_RU[value.weekday()]} {value:%H:%M}"
    )


def _service_label(value: str) -> str:
    return "Стрижка" if value == "haircut" else value


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
