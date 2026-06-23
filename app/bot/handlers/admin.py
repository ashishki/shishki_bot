"""Admin command and callback guards."""

from __future__ import annotations

from dataclasses import dataclass

from app.bot.keyboards import (
    ADMIN_CALLBACK_PREFIX,
    AdminMenuAction,
    MenuButton,
    admin_callback_data,
    admin_menu_buttons,
    parse_admin_callback_data,
)
from app.config import Settings

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
