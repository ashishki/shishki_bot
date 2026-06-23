"""Client command and booking flow handlers."""

from __future__ import annotations

from collections.abc import Callable
from contextlib import AbstractAsyncContextManager, AbstractContextManager
from dataclasses import dataclass
from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker
from sqlalchemy.orm import Session

from app.bot.keyboards import (
    CLIENT_CALLBACK_PREFIX,
    ClientMenuAction,
    MenuButton,
    client_callback_data,
    client_menu_buttons,
    parse_client_callback_data,
)
from app.bot.messages import booking_confirmation_message
from app.config import Settings
from app.db.models import Booking, BookingStatus, Client, Slot, User
from app.services.booking import (
    DEFAULT_HAIRCUT_DURATION_MINUTES,
    DEFAULT_HAIRCUT_PRICE,
    SlotUnavailableError,
    create_haircut_booking,
    list_available_slots,
)

HAIRCUT_PRICE_LABEL = str(DEFAULT_HAIRCUT_PRICE).rstrip("0").rstrip(".")

CLIENT_WELCOME_TEXT = "\n".join(
    [
        "Welcome to SHISHKI booking",
        f"Haircut: {DEFAULT_HAIRCUT_DURATION_MINUTES} minutes, "
        f"{HAIRCUT_PRICE_LABEL} GEL.",
        "Coloring and complex services require a personal consultation.",
    ]
)
NO_AVAILABLE_SLOTS_TEXT = "No available haircut slots right now."
HAIRCUT_SLOT_LIST_TEXT = "Choose an available haircut slot."
HAIRCUT_CONFIRM_TEXT = "Confirm this haircut booking?"
NO_ACTIVE_BOOKING_TEXT = "You do not have an active booking."
SLOT_UNAVAILABLE_TEXT = "That slot is no longer available."
IDENTITY_REQUIRED_TEXT = "Telegram user identity is required for booking."
UNKNOWN_ACTION_TEXT = "Unknown action."
BOOKING_UNAVAILABLE_TEXT = "Booking is temporarily unavailable."


class ClientIdentityRequired(ValueError):
    """Raised when a booking action has no Telegram user identity."""


@dataclass(frozen=True, slots=True)
class ClientMenuResponse:
    text: str
    buttons: tuple[MenuButton, ...]


@dataclass(frozen=True, slots=True)
class SlotOption:
    slot_id: int
    label: str
    callback_data: str


@dataclass(frozen=True, slots=True)
class SlotListResponse:
    text: str
    slots: tuple[SlotOption, ...]


@dataclass(frozen=True, slots=True)
class ClientTextResponse:
    text: str


@dataclass(frozen=True, slots=True)
class ClientBookingResponse:
    text: str
    booking: Booking


@dataclass(frozen=True, slots=True)
class ClientCallbackResponse:
    text: str
    slots: tuple[SlotOption, ...] = ()
    buttons: tuple[MenuButton, ...] = ()
    should_commit: bool = False


def handle_start_command(settings: Settings) -> ClientMenuResponse:
    return ClientMenuResponse(
        text=CLIENT_WELCOME_TEXT,
        buttons=client_menu_buttons(),
    )


def handle_unknown_input(settings: Settings) -> ClientMenuResponse:
    return handle_start_command(settings)


def handle_haircut_booking_start(
    session: Session,
    settings: Settings,
    *,
    now: datetime | None = None,
) -> SlotListResponse:
    slots = tuple(list_available_slots(session, now=now))
    if not slots:
        return SlotListResponse(text=NO_AVAILABLE_SLOTS_TEXT, slots=())

    return SlotListResponse(
        text=HAIRCUT_SLOT_LIST_TEXT,
        slots=tuple(_slot_option(slot, settings) for slot in slots),
    )


def handle_haircut_slot_selection(
    session: Session,
    settings: Settings,
    *,
    slot_id: int,
    now: datetime | None = None,
) -> ClientTextResponse:
    available_slot_ids = {
        slot.id
        for slot in list_available_slots(session, now=now)
        if slot.id is not None
    }
    if slot_id not in available_slot_ids:
        raise SlotUnavailableError(f"Slot is unavailable: {slot_id}")

    slot = session.get(Slot, slot_id)
    if slot is None:
        raise SlotUnavailableError(f"Slot is unavailable: {slot_id}")

    return ClientTextResponse(
        text="\n".join(
            [
                HAIRCUT_CONFIRM_TEXT,
                f"Date/time: {_format_slot_label(slot, settings)}",
                f"Place: {slot.place}",
                f"Duration: {DEFAULT_HAIRCUT_DURATION_MINUTES} minutes",
                f"Price: {HAIRCUT_PRICE_LABEL} GEL",
            ]
        )
    )


def handle_haircut_booking_confirmation(
    session: Session,
    settings: Settings,
    *,
    telegram_user_id: int | None,
    slot_id: int,
    display_name: str | None = None,
    username: str | None = None,
) -> ClientBookingResponse:
    if telegram_user_id is None:
        raise ClientIdentityRequired("Telegram user identity is required")

    client = get_or_create_client(
        session,
        telegram_user_id=telegram_user_id,
        display_name=display_name,
        username=username,
    )
    booking = create_haircut_booking(session, client_id=client.id, slot_id=slot_id)
    return ClientBookingResponse(
        text=booking_confirmation_message(
            booking,
            timezone=settings.timezone_info,
        ),
        booking=booking,
    )


def handle_client_callback_payload(
    session: Session | None,
    settings: Settings,
    *,
    callback_payload: str | None,
    telegram_user_id: int | None,
    display_name: str | None = None,
    username: str | None = None,
    now: datetime | None = None,
) -> ClientCallbackResponse:
    try:
        parsed = parse_client_callback_data(callback_payload)
    except ValueError:
        return ClientCallbackResponse(text=UNKNOWN_ACTION_TEXT)

    if parsed.action is ClientMenuAction.COMPLEX_SERVICE:
        response = handle_complex_service_redirect(settings)
        return ClientCallbackResponse(text=response.text)

    if parsed.action is ClientMenuAction.CONTACT:
        response = handle_contact_request(settings)
        return ClientCallbackResponse(text=response.text)

    if parsed.action is ClientMenuAction.RESCHEDULE_CANCEL:
        response = handle_reschedule_cancel_request(settings)
        return ClientCallbackResponse(text=response.text)

    if session is None:
        return ClientCallbackResponse(text=BOOKING_UNAVAILABLE_TEXT)

    if parsed.action is ClientMenuAction.BOOK_HAIRCUT:
        response = handle_haircut_booking_start(session, settings, now=now)
        return ClientCallbackResponse(text=response.text, slots=response.slots)

    if parsed.action is ClientMenuAction.MY_BOOKING:
        try:
            response = handle_active_booking_view(
                session,
                settings,
                telegram_user_id=telegram_user_id,
                now=now,
            )
        except ClientIdentityRequired:
            return ClientCallbackResponse(text=IDENTITY_REQUIRED_TEXT)
        return ClientCallbackResponse(text=response.text)

    if parsed.action is ClientMenuAction.SELECT_HAIRCUT_SLOT:
        try:
            slot_id = _parse_slot_id(parsed.value)
            response = handle_haircut_slot_selection(
                session,
                settings,
                slot_id=slot_id,
                now=now,
            )
        except (SlotUnavailableError, ValueError):
            return ClientCallbackResponse(text=SLOT_UNAVAILABLE_TEXT)

        return ClientCallbackResponse(
            text=response.text,
            buttons=(
                MenuButton(
                    action=ClientMenuAction.CONFIRM_HAIRCUT,
                    label="Confirm booking",
                    callback_data=client_callback_data(
                        ClientMenuAction.CONFIRM_HAIRCUT,
                        slot_id,
                    ),
                ),
            ),
        )

    if parsed.action is ClientMenuAction.CONFIRM_HAIRCUT:
        try:
            slot_id = _parse_slot_id(parsed.value)
            response = handle_haircut_booking_confirmation(
                session,
                settings,
                telegram_user_id=telegram_user_id,
                slot_id=slot_id,
                display_name=display_name,
                username=username,
            )
        except SlotUnavailableError:
            return ClientCallbackResponse(text=SLOT_UNAVAILABLE_TEXT)
        except ClientIdentityRequired:
            return ClientCallbackResponse(text=IDENTITY_REQUIRED_TEXT)
        except ValueError:
            return ClientCallbackResponse(text=UNKNOWN_ACTION_TEXT)
        return ClientCallbackResponse(text=response.text, should_commit=True)

    return ClientCallbackResponse(text=UNKNOWN_ACTION_TEXT)


def handle_complex_service_redirect(settings: Settings) -> ClientTextResponse:
    contact = _contact_target(settings)
    return ClientTextResponse(
        text="\n".join(
            [
                "Coloring and complex services need a personal consultation.",
                f"Contact the stylist: {contact}",
                "The stylist will create the booking manually after consultation.",
            ]
        )
    )


def handle_contact_request(settings: Settings) -> ClientTextResponse:
    return ClientTextResponse(text=f"Contact the stylist: {_contact_target(settings)}")


def handle_active_booking_view(
    session: Session,
    settings: Settings,
    *,
    telegram_user_id: int | None,
    now: datetime | None = None,
) -> ClientTextResponse:
    if telegram_user_id is None:
        raise ClientIdentityRequired("Telegram user identity is required")

    booking = _active_booking_for_user(session, telegram_user_id, now=now)
    if booking is None:
        return ClientTextResponse(text=NO_ACTIVE_BOOKING_TEXT)

    return ClientTextResponse(
        text="Your active booking\n"
        + booking_confirmation_message(booking, timezone=settings.timezone_info)
    )


def handle_reschedule_cancel_request(settings: Settings) -> ClientTextResponse:
    return ClientTextResponse(
        text="\n".join(
            [
                "To reschedule or cancel, contact the stylist.",
                f"Contact: {_contact_target(settings)}",
            ]
        )
    )


def get_or_create_client(
    session: Session,
    *,
    telegram_user_id: int,
    display_name: str | None = None,
    username: str | None = None,
) -> Client:
    user = session.scalar(select(User).where(User.telegram_id == telegram_user_id))
    if user is None:
        user = User(
            telegram_id=telegram_user_id,
            username=username,
            display_name=display_name,
        )
        client = Client(user=user, display_name=display_name)
        session.add(client)
        session.flush()
        return client

    if username:
        user.username = username
    if display_name:
        user.display_name = display_name

    client = user.client
    if client is None:
        client = Client(user=user, display_name=display_name or user.display_name)
        session.add(client)
    elif display_name:
        client.display_name = display_name

    session.flush()
    return client


async def dispatch_client_callback_async(
    async_session_factory: async_sessionmaker[AsyncSession],
    settings: Settings,
    *,
    callback_payload: str | None,
    telegram_user_id: int | None,
    display_name: str | None = None,
    username: str | None = None,
    now: datetime | None = None,
) -> ClientCallbackResponse:
    async with async_session_factory() as async_session:
        response = await async_session.run_sync(
            lambda sync_session: handle_client_callback_payload(
                sync_session,
                settings,
                callback_payload=callback_payload,
                telegram_user_id=telegram_user_id,
                display_name=display_name,
                username=username,
                now=now,
            )
        )
        if response.should_commit:
            await async_session.commit()
        else:
            await async_session.rollback()
        return response


def build_client_router(
    settings: Settings,
    *,
    session_factory: Callable[[], AbstractContextManager[Session]] | None = None,
    async_session_factory: Callable[
        [],
        AbstractAsyncContextManager[AsyncSession],
    ]
    | None = None,
):
    """Build the aiogram router for client commands and callback actions."""

    try:
        from aiogram import F, Router
        from aiogram.filters import CommandStart
        from aiogram.types import (
            CallbackQuery,
            InlineKeyboardButton,
            InlineKeyboardMarkup,
            Message,
        )
    except ImportError as exc:  # pragma: no cover - exercised only without deps
        raise RuntimeError(
            "aiogram is required to build client handlers; install requirements.txt"
        ) from exc

    router = Router(name="client")

    @router.message(CommandStart())
    async def start_menu(message: Message) -> None:
        response = handle_start_command(settings)
        await message.answer(
            response.text,
            reply_markup=_buttons_to_keyboard(response.buttons),
        )

    @router.callback_query(F.data.startswith(f"{CLIENT_CALLBACK_PREFIX}:"))
    async def client_callback(callback: CallbackQuery) -> None:
        response = await _dispatch_callback(callback)
        await callback.answer()
        if callback.message:
            await callback.message.answer(
                response.text,
                reply_markup=_callback_keyboard(response),
            )

    @router.message()
    async def unknown_input(message: Message) -> None:
        response = handle_unknown_input(settings)
        await message.answer(
            response.text,
            reply_markup=_buttons_to_keyboard(response.buttons),
        )

    async def _dispatch_callback(callback: CallbackQuery) -> ClientCallbackResponse:
        kwargs = _callback_kwargs(callback)
        if async_session_factory is not None:
            return await dispatch_client_callback_async(
                async_session_factory,
                settings,
                **kwargs,
            )

        if session_factory is not None:
            with session_factory() as session:
                response = handle_client_callback_payload(session, settings, **kwargs)
                if response.should_commit:
                    session.commit()
                else:
                    session.rollback()
                return response

        return handle_client_callback_payload(None, settings, **kwargs)

    def _callback_kwargs(callback: CallbackQuery) -> dict[str, object]:
        user = callback.from_user
        return {
            "callback_payload": callback.data,
            "telegram_user_id": user.id if user else None,
            "display_name": user.full_name if user else None,
            "username": user.username if user else None,
        }

    def _callback_keyboard(
        response: ClientCallbackResponse,
    ) -> InlineKeyboardMarkup | None:
        if response.slots:
            return _slots_to_keyboard(response.slots)
        if response.buttons:
            return _buttons_to_keyboard(response.buttons)
        return None

    def _buttons_to_keyboard(buttons: tuple[MenuButton, ...]) -> InlineKeyboardMarkup:
        return InlineKeyboardMarkup(
            inline_keyboard=[
                [
                    InlineKeyboardButton(
                        text=button.label,
                        callback_data=button.callback_data,
                    )
                ]
                for button in buttons
            ]
        )

    def _slots_to_keyboard(slots: tuple[SlotOption, ...]) -> InlineKeyboardMarkup:
        return InlineKeyboardMarkup(
            inline_keyboard=[
                [
                    InlineKeyboardButton(
                        text=slot.label,
                        callback_data=slot.callback_data,
                    )
                ]
                for slot in slots
            ]
        )

    return router


def _slot_option(slot: Slot, settings: Settings) -> SlotOption:
    if slot.id is None:
        raise ValueError("Slot must be flushed before it can be rendered")
    return SlotOption(
        slot_id=slot.id,
        label=_format_slot_label(slot, settings),
        callback_data=client_callback_data(
            ClientMenuAction.SELECT_HAIRCUT_SLOT,
            slot.id,
        ),
    )


def _format_slot_label(slot: Slot, settings: Settings) -> str:
    starts_at = slot.starts_at
    if starts_at.tzinfo is None:
        starts_at = starts_at.replace(tzinfo=settings.timezone_info)
    starts_at = starts_at.astimezone(settings.timezone_info)
    return starts_at.strftime("%Y-%m-%d %H:%M")


def _contact_target(settings: Settings) -> str:
    return settings.stylist_contact_url


def _active_booking_for_user(
    session: Session,
    telegram_user_id: int,
    *,
    now: datetime | None = None,
) -> Booking | None:
    cutoff = now or datetime.now(UTC)
    return session.scalar(
        select(Booking)
        .join(Client)
        .join(User)
        .where(
            User.telegram_id == telegram_user_id,
            Booking.starts_at > cutoff,
            Booking.status.in_([BookingStatus.CONFIRMED, BookingStatus.RESCHEDULED]),
        )
        .order_by(Booking.starts_at)
        .limit(1)
    )


def _parse_slot_id(raw_value: str | None) -> int:
    if raw_value is None:
        raise ValueError("Missing slot ID")
    try:
        return int(raw_value)
    except ValueError as exc:
        raise ValueError("Invalid slot ID") from exc
