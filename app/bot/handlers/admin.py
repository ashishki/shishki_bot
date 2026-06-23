"""Admin command and callback guards."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal

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
from app.db.models import Booking, NotificationLog
from app.services.booking import (
    cancel_booking_by_admin,
    create_manual_booking,
    reschedule_booking,
    update_booking_details_by_admin,
)
from app.services.finance import (
    ExpenseInput,
    WeeklyRevenueSummary,
    complete_booking,
    weekly_revenue_summary,
)
from app.services.notifications import NotificationSender, send_client_notification

ADMIN_MENU_TEXT = "Admin menu"
ADMIN_ACCESS_DENIED_TEXT = "Admin access denied"
UNKNOWN_ADMIN_ACTION_TEXT = "Unknown admin action"


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
        text=booking_rescheduled_message(booking, timezone=settings.timezone_info),
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
            text=booking_updated_message(booking, timezone=settings.timezone_info),
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


def build_admin_router(settings: Settings):
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
        )

    @router.callback_query(F.data.startswith(f"{ADMIN_CALLBACK_PREFIX}:"))
    async def admin_callback(callback: CallbackQuery) -> None:
        telegram_user_id = callback.from_user.id if callback.from_user else None
        try:
            response = handle_admin_callback(telegram_user_id, settings, callback.data)
        except AdminAccessDenied:
            await callback.answer(ADMIN_ACCESS_DENIED_TEXT, show_alert=True)
            return
        except ValueError:
            await callback.answer(UNKNOWN_ADMIN_ACTION_TEXT, show_alert=True)
            return

        await callback.answer()
        if callback.message:
            await callback.message.answer(response.text)

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

    return router
