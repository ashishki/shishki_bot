"""Client command and booking flow handlers."""

from __future__ import annotations

from collections.abc import Callable
from contextlib import AbstractAsyncContextManager, AbstractContextManager
from dataclasses import dataclass
from datetime import UTC, date, datetime
from html import escape
from pathlib import Path

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
from app.bot.messages import (
    booking_cancelled_message,
    booking_confirmation_message,
    booking_rescheduled_message,
    format_location_line,
)
from app.config import Settings
from app.db.models import Booking, BookingStatus, Client, Slot, User
from app.services.booking import (
    DEFAULT_HAIRCUT_DURATION_MINUTES,
    DEFAULT_HAIRCUT_PRICE,
    SlotUnavailableError,
    cancel_booking_by_client,
    create_haircut_booking,
    list_available_slots,
    reschedule_booking_by_client,
)

HAIRCUT_PRICE_LABEL = str(DEFAULT_HAIRCUT_PRICE).rstrip("0").rstrip(".")

CLIENT_WELCOME_TEXT = "\n".join(
    [
        "SHISHKI",
        f"Стрижка: {DEFAULT_HAIRCUT_DURATION_MINUTES} мин, {HAIRCUT_PRICE_LABEL} GEL.",
        "Выберите удобную дату ниже.",
    ]
)
NO_AVAILABLE_SLOTS_TEXT = "Свободных дат пока нет."
HAIRCUT_DATE_LIST_TEXT = "Выберите дату для стрижки."
HAIRCUT_SLOT_LIST_TEXT = "Выберите время:"
HAIRCUT_CONFIRM_TEXT = "Подтвердить запись?"
NO_ACTIVE_BOOKING_TEXT = "У вас пока нет активной записи."
CHANGE_BOOKING_DATE_TEXT = "Выберите новую дату."
CANCEL_BOOKING_CONFIRM_TEXT = "Точно отменить эту запись?"
SLOT_UNAVAILABLE_TEXT = "Это время уже недоступно. Выберите другое."
IDENTITY_REQUIRED_TEXT = "Не удалось определить ваш Telegram-профиль."
UNKNOWN_ACTION_TEXT = "Неизвестное действие."
BOOKING_UNAVAILABLE_TEXT = "Запись временно недоступна."
PROJECT_ROOT = Path(__file__).resolve().parents[3]
ABOUT_MASTER_TEXT_PATH = PROJECT_ROOT / "about_me.md"
ABOUT_MASTER_PHOTO_PATH = PROJECT_ROOT / "IMG_9385.PNG"


class ClientIdentityRequired(ValueError):
    """Raised when a booking action has no Telegram user identity."""


class ClientActiveBookingRequired(ValueError):
    """Raised when a client action requires an active booking."""


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
    buttons: tuple[MenuButton, ...] = ()


@dataclass(frozen=True, slots=True)
class ClientTextResponse:
    text: str
    buttons: tuple[MenuButton, ...] = ()


@dataclass(frozen=True, slots=True)
class ClientBookingResponse:
    text: str
    booking: Booking
    buttons: tuple[MenuButton, ...] = ()


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
) -> ClientMenuResponse:
    slots = tuple(list_available_slots(session, now=now))
    if not slots:
        return ClientMenuResponse(text=NO_AVAILABLE_SLOTS_TEXT, buttons=())

    return ClientMenuResponse(
        text=HAIRCUT_DATE_LIST_TEXT,
        buttons=_date_buttons(slots, settings) + (_my_booking_button(),),
    )


def handle_haircut_date_selection(
    session: Session,
    settings: Settings,
    *,
    selected_date: date,
    now: datetime | None = None,
) -> SlotListResponse:
    slots = tuple(
        slot
        for slot in list_available_slots(session, now=now)
        if _slot_local_date(slot, settings) == selected_date
    )
    if not slots:
        return SlotListResponse(
            text=NO_AVAILABLE_SLOTS_TEXT,
            slots=(),
            buttons=(_dates_button(),),
        )

    return SlotListResponse(
        text=f"{HAIRCUT_SLOT_LIST_TEXT} {_format_date_label(selected_date)}",
        slots=tuple(_slot_option(slot, settings) for slot in slots),
        buttons=(_dates_button(label="Назад к датам"), _my_booking_button()),
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
                f"Время: {_format_slot_label(slot, settings)}",
                _settings_location_line(slot.place, settings),
                f"Длительность: {DEFAULT_HAIRCUT_DURATION_MINUTES} мин",
                f"Цена: {HAIRCUT_PRICE_LABEL} GEL",
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
            **_settings_location_links(settings),
        ),
        booking=booking,
        buttons=(_my_booking_button(), _dates_button()),
    )


def handle_client_booking_cancellation(
    session: Session,
    settings: Settings,
    *,
    telegram_user_id: int | None,
    now: datetime | None = None,
) -> ClientBookingResponse:
    booking = _require_active_booking_for_user(
        session,
        telegram_user_id=telegram_user_id,
        now=now,
    )
    booking = cancel_booking_by_client(session, booking_id=booking.id)
    return ClientBookingResponse(
        text=booking_cancelled_message(
            booking,
            reason="отменено клиентом",
            timezone=settings.timezone_info,
            **_settings_location_links(settings),
        ),
        booking=booking,
        buttons=(_dates_button(),),
    )


def handle_client_booking_reschedule(
    session: Session,
    settings: Settings,
    *,
    telegram_user_id: int | None,
    new_slot_id: int,
    now: datetime | None = None,
) -> ClientBookingResponse:
    booking = _require_active_booking_for_user(
        session,
        telegram_user_id=telegram_user_id,
        now=now,
    )
    booking = reschedule_booking_by_client(
        session,
        booking_id=booking.id,
        new_slot_id=new_slot_id,
    )
    return ClientBookingResponse(
        text=booking_rescheduled_message(
            booking,
            timezone=settings.timezone_info,
            **_settings_location_links(settings),
        ),
        booking=booking,
        buttons=(_my_booking_button(), _dates_button()),
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

    if parsed.action == ClientMenuAction.COMPLEX_SERVICE:
        response = handle_complex_service_redirect(settings)
        return ClientCallbackResponse(text=response.text)

    if parsed.action == ClientMenuAction.ABOUT_MASTER:
        response = handle_about_master_request()
        return ClientCallbackResponse(text=response.text, buttons=response.buttons)

    if parsed.action == ClientMenuAction.CONTACT:
        response = handle_contact_request(settings)
        return ClientCallbackResponse(text=response.text)

    if session is None:
        return ClientCallbackResponse(text=BOOKING_UNAVAILABLE_TEXT)

    if parsed.action == ClientMenuAction.BOOK_HAIRCUT:
        response = handle_haircut_booking_start(session, settings, now=now)
        return ClientCallbackResponse(text=response.text, buttons=response.buttons)

    if parsed.action in (
        ClientMenuAction.MY_BOOKING,
        ClientMenuAction.RESCHEDULE_CANCEL,
    ):
        try:
            response = handle_active_booking_view(
                session,
                settings,
                telegram_user_id=telegram_user_id,
                now=now,
            )
        except ClientIdentityRequired:
            return ClientCallbackResponse(text=IDENTITY_REQUIRED_TEXT)
        return ClientCallbackResponse(text=response.text, buttons=response.buttons)

    if parsed.action == ClientMenuAction.CHANGE_BOOKING:
        try:
            response = handle_reschedule_date_start(
                session,
                settings,
                telegram_user_id=telegram_user_id,
                now=now,
            )
        except ClientIdentityRequired:
            return ClientCallbackResponse(text=IDENTITY_REQUIRED_TEXT)
        except ClientActiveBookingRequired:
            return _no_active_booking_response()
        return ClientCallbackResponse(text=response.text, buttons=response.buttons)

    if parsed.action == ClientMenuAction.SELECT_RESCHEDULE_DATE:
        try:
            selected_date = _parse_date(parsed.value)
            response = handle_reschedule_date_selection(
                session,
                settings,
                telegram_user_id=telegram_user_id,
                selected_date=selected_date,
                now=now,
            )
        except ClientIdentityRequired:
            return ClientCallbackResponse(text=IDENTITY_REQUIRED_TEXT)
        except ClientActiveBookingRequired:
            return _no_active_booking_response()
        except ValueError:
            return ClientCallbackResponse(text=UNKNOWN_ACTION_TEXT)
        return ClientCallbackResponse(
            text=response.text,
            slots=response.slots,
            buttons=response.buttons,
        )

    if parsed.action == ClientMenuAction.SELECT_RESCHEDULE_SLOT:
        try:
            slot_id = _parse_slot_id(parsed.value)
            response = handle_reschedule_slot_selection(
                session,
                settings,
                telegram_user_id=telegram_user_id,
                slot_id=slot_id,
                now=now,
            )
        except ClientIdentityRequired:
            return ClientCallbackResponse(text=IDENTITY_REQUIRED_TEXT)
        except ClientActiveBookingRequired:
            return _no_active_booking_response()
        except (SlotUnavailableError, ValueError):
            return ClientCallbackResponse(text=SLOT_UNAVAILABLE_TEXT)
        return ClientCallbackResponse(text=response.text, buttons=response.buttons)

    if parsed.action == ClientMenuAction.CONFIRM_RESCHEDULE:
        try:
            slot_id = _parse_slot_id(parsed.value)
            response = handle_client_booking_reschedule(
                session,
                settings,
                telegram_user_id=telegram_user_id,
                new_slot_id=slot_id,
                now=now,
            )
        except ClientIdentityRequired:
            return ClientCallbackResponse(text=IDENTITY_REQUIRED_TEXT)
        except ClientActiveBookingRequired:
            return _no_active_booking_response()
        except (SlotUnavailableError, ValueError):
            return ClientCallbackResponse(text=SLOT_UNAVAILABLE_TEXT)
        return ClientCallbackResponse(
            text=response.text,
            buttons=response.buttons,
            should_commit=True,
        )

    if parsed.action == ClientMenuAction.CANCEL_BOOKING:
        try:
            response = handle_cancel_booking_prompt(
                session,
                settings,
                telegram_user_id=telegram_user_id,
                now=now,
            )
        except ClientIdentityRequired:
            return ClientCallbackResponse(text=IDENTITY_REQUIRED_TEXT)
        except ClientActiveBookingRequired:
            return _no_active_booking_response()
        return ClientCallbackResponse(text=response.text, buttons=response.buttons)

    if parsed.action == ClientMenuAction.CONFIRM_CANCEL:
        try:
            response = handle_client_booking_cancellation(
                session,
                settings,
                telegram_user_id=telegram_user_id,
                now=now,
            )
        except ClientIdentityRequired:
            return ClientCallbackResponse(text=IDENTITY_REQUIRED_TEXT)
        except ClientActiveBookingRequired:
            return _no_active_booking_response()
        return ClientCallbackResponse(
            text=response.text,
            buttons=response.buttons,
            should_commit=True,
        )

    if parsed.action == ClientMenuAction.SELECT_HAIRCUT_DATE:
        try:
            selected_date = _parse_date(parsed.value)
        except ValueError:
            return ClientCallbackResponse(text=UNKNOWN_ACTION_TEXT)
        response = handle_haircut_date_selection(
            session,
            settings,
            selected_date=selected_date,
            now=now,
        )
        return ClientCallbackResponse(
            text=response.text,
            slots=response.slots,
            buttons=response.buttons,
        )

    if parsed.action == ClientMenuAction.SELECT_HAIRCUT_SLOT:
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
                    label="Подтвердить запись",
                    callback_data=client_callback_data(
                        ClientMenuAction.CONFIRM_HAIRCUT,
                        slot_id,
                    ),
                ),
                _slot_back_button(session, settings, slot_id),
            ),
        )

    if parsed.action == ClientMenuAction.CONFIRM_HAIRCUT:
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
        return ClientCallbackResponse(
            text=response.text,
            buttons=response.buttons,
            should_commit=True,
        )

    return ClientCallbackResponse(text=UNKNOWN_ACTION_TEXT)


def handle_complex_service_redirect(settings: Settings) -> ClientTextResponse:
    contact = _contact_target(settings)
    return ClientTextResponse(
        text="\n".join(
            [
                "Окрашивание и сложные услуги требуют консультации.",
                f"Напишите стилисту: {contact}",
                "После консультации запись будет создана вручную.",
            ]
        )
    )


def handle_about_master_request() -> ClientTextResponse:
    return ClientTextResponse(
        text=_about_master_text(),
        buttons=(_dates_button(label="Записаться"), _contact_button()),
    )


def handle_contact_request(settings: Settings) -> ClientTextResponse:
    return ClientTextResponse(
        text=f"Связаться со стилистом: {_contact_target(settings)}"
    )


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
        return ClientTextResponse(
            text=NO_ACTIVE_BOOKING_TEXT,
            buttons=(_dates_button(),),
        )

    return ClientTextResponse(
        text="Ваша активная запись\n"
        + booking_confirmation_message(
            booking,
            timezone=settings.timezone_info,
            **_settings_location_links(settings),
        ),
        buttons=(
            _change_booking_button(),
            _cancel_booking_button(),
            _dates_button(),
        ),
    )


def handle_reschedule_date_start(
    session: Session,
    settings: Settings,
    *,
    telegram_user_id: int | None,
    now: datetime | None = None,
) -> ClientMenuResponse:
    _require_active_booking_for_user(
        session,
        telegram_user_id=telegram_user_id,
        now=now,
    )
    slots = tuple(list_available_slots(session, now=now))
    if not slots:
        return ClientMenuResponse(
            text=NO_AVAILABLE_SLOTS_TEXT,
            buttons=(_my_booking_button(),),
        )
    return ClientMenuResponse(
        text=CHANGE_BOOKING_DATE_TEXT,
        buttons=_date_buttons(
            slots,
            settings,
            action=ClientMenuAction.SELECT_RESCHEDULE_DATE,
        )
        + (_my_booking_button(label="Назад к моей записи"),),
    )


def handle_reschedule_date_selection(
    session: Session,
    settings: Settings,
    *,
    telegram_user_id: int | None,
    selected_date: date,
    now: datetime | None = None,
) -> SlotListResponse:
    _require_active_booking_for_user(
        session,
        telegram_user_id=telegram_user_id,
        now=now,
    )
    slots = tuple(
        slot
        for slot in list_available_slots(session, now=now)
        if _slot_local_date(slot, settings) == selected_date
    )
    if not slots:
        return SlotListResponse(
            text=NO_AVAILABLE_SLOTS_TEXT,
            slots=(),
            buttons=(_change_booking_button(label="Назад к датам"),),
        )
    return SlotListResponse(
        text=f"{HAIRCUT_SLOT_LIST_TEXT} {_format_date_label(selected_date)}",
        slots=tuple(
            _slot_option(
                slot,
                settings,
                action=ClientMenuAction.SELECT_RESCHEDULE_SLOT,
            )
            for slot in slots
        ),
        buttons=(
            _change_booking_button(label="Назад к датам"),
            _my_booking_button(),
        ),
    )


def handle_reschedule_slot_selection(
    session: Session,
    settings: Settings,
    *,
    telegram_user_id: int | None,
    slot_id: int,
    now: datetime | None = None,
) -> ClientTextResponse:
    _require_active_booking_for_user(
        session,
        telegram_user_id=telegram_user_id,
        now=now,
    )
    response = handle_haircut_slot_selection(
        session,
        settings,
        slot_id=slot_id,
        now=now,
    )
    return ClientTextResponse(
        text=response.text.replace(HAIRCUT_CONFIRM_TEXT, "Подтвердить новое время?"),
        buttons=(
            MenuButton(
                action=ClientMenuAction.CONFIRM_RESCHEDULE,
                label="Подтвердить перенос",
                callback_data=client_callback_data(
                    ClientMenuAction.CONFIRM_RESCHEDULE,
                    slot_id,
                ),
            ),
            _reschedule_slot_back_button(session, settings, slot_id),
        ),
    )


def handle_cancel_booking_prompt(
    session: Session,
    settings: Settings,
    *,
    telegram_user_id: int | None,
    now: datetime | None = None,
) -> ClientTextResponse:
    booking = _require_active_booking_for_user(
        session,
        telegram_user_id=telegram_user_id,
        now=now,
    )
    return ClientTextResponse(
        text=CANCEL_BOOKING_CONFIRM_TEXT
        + "\n"
        + booking_confirmation_message(
            booking,
            timezone=settings.timezone_info,
            **_settings_location_links(settings),
        ),
        buttons=(
            MenuButton(
                action=ClientMenuAction.CONFIRM_CANCEL,
                label="Да, отменить",
                callback_data=client_callback_data(ClientMenuAction.CONFIRM_CANCEL),
            ),
            _my_booking_button(label="Оставить запись"),
        ),
    )


def handle_reschedule_cancel_request(settings: Settings) -> ClientTextResponse:
    return ClientTextResponse(
        text="\n".join(
            [
                "Перенести или отменить запись можно в разделе «Моя запись».",
                f"Если нужно обсудить детали: {_contact_target(settings)}",
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
            FSInputFile,
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
        if async_session_factory is None and session_factory is None:
            response = handle_start_command(settings)
            await message.answer(
                response.text,
                reply_markup=_buttons_to_keyboard(response.buttons),
                parse_mode="HTML",
            )
            return

        response = await _dispatch_payload(
            callback_payload=client_callback_data(ClientMenuAction.BOOK_HAIRCUT),
            telegram_user_id=message.from_user.id if message.from_user else None,
            display_name=message.from_user.full_name if message.from_user else None,
            username=message.from_user.username if message.from_user else None,
        )
        await message.answer(
            response.text,
            reply_markup=_callback_keyboard(response),
            parse_mode="HTML",
        )

    @router.callback_query(F.data.startswith(f"{CLIENT_CALLBACK_PREFIX}:"))
    async def client_callback(callback: CallbackQuery) -> None:
        if _is_about_master_callback(callback.data):
            await callback.answer()
            if callback.message:
                response = handle_about_master_request()
                await callback.message.answer_photo(
                    photo=FSInputFile(ABOUT_MASTER_PHOTO_PATH),
                    caption=_html_caption(response.text),
                    reply_markup=_buttons_to_keyboard(response.buttons),
                    parse_mode="HTML",
                )
            return

        response = await _dispatch_callback(callback)
        await callback.answer()
        if callback.message:
            await callback.message.answer(
                response.text,
                reply_markup=_callback_keyboard(response),
                parse_mode="HTML",
            )

    @router.message()
    async def unknown_input(message: Message) -> None:
        response = handle_unknown_input(settings)
        await message.answer(
            response.text,
            reply_markup=_buttons_to_keyboard(response.buttons),
            parse_mode="HTML",
        )

    async def _dispatch_callback(callback: CallbackQuery) -> ClientCallbackResponse:
        return await _dispatch_payload(**_callback_kwargs(callback))

    async def _dispatch_payload(**kwargs: object) -> ClientCallbackResponse:
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
        if response.slots or response.buttons:
            return _callback_buttons_to_keyboard(response.slots, response.buttons)
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

    def _callback_buttons_to_keyboard(
        slots: tuple[SlotOption, ...],
        buttons: tuple[MenuButton, ...],
    ) -> InlineKeyboardMarkup:
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
            + [
                [
                    InlineKeyboardButton(
                        text=button.label,
                        callback_data=button.callback_data,
                    )
                ]
                for button in buttons
            ],
        )

    return router


def _is_about_master_callback(payload: str | None) -> bool:
    try:
        parsed = parse_client_callback_data(payload)
    except ValueError:
        return False
    return parsed.action == ClientMenuAction.ABOUT_MASTER


def _slot_option(
    slot: Slot,
    settings: Settings,
    *,
    action: ClientMenuAction = ClientMenuAction.SELECT_HAIRCUT_SLOT,
) -> SlotOption:
    if slot.id is None:
        raise ValueError("Slot must be flushed before it can be rendered")
    return SlotOption(
        slot_id=slot.id,
        label=_format_slot_label(slot, settings),
        callback_data=client_callback_data(
            action,
            slot.id,
        ),
    )


def _date_buttons(
    slots: tuple[Slot, ...],
    settings: Settings,
    *,
    action: ClientMenuAction = ClientMenuAction.SELECT_HAIRCUT_DATE,
) -> tuple[MenuButton, ...]:
    dates = sorted({_slot_local_date(slot, settings) for slot in slots})
    return tuple(
        MenuButton(
            action=action,
            label=_format_date_label(value),
            callback_data=client_callback_data(
                action,
                value.isoformat(),
            ),
        )
        for value in dates
    )


def _dates_button(*, label: str = "Даты") -> MenuButton:
    return MenuButton(
        action=ClientMenuAction.BOOK_HAIRCUT,
        label=label,
        callback_data=client_callback_data(ClientMenuAction.BOOK_HAIRCUT),
    )


def _my_booking_button(*, label: str = "Моя запись") -> MenuButton:
    return MenuButton(
        action=ClientMenuAction.MY_BOOKING,
        label=label,
        callback_data=client_callback_data(ClientMenuAction.MY_BOOKING),
    )


def _contact_button(*, label: str = "Связаться") -> MenuButton:
    return MenuButton(
        action=ClientMenuAction.CONTACT,
        label=label,
        callback_data=client_callback_data(ClientMenuAction.CONTACT),
    )


def _change_booking_button(*, label: str = "Перенести") -> MenuButton:
    return MenuButton(
        action=ClientMenuAction.CHANGE_BOOKING,
        label=label,
        callback_data=client_callback_data(ClientMenuAction.CHANGE_BOOKING),
    )


def _cancel_booking_button(*, label: str = "Отменить") -> MenuButton:
    return MenuButton(
        action=ClientMenuAction.CANCEL_BOOKING,
        label=label,
        callback_data=client_callback_data(ClientMenuAction.CANCEL_BOOKING),
    )


def _no_active_booking_response() -> ClientCallbackResponse:
    return ClientCallbackResponse(
        text=NO_ACTIVE_BOOKING_TEXT,
        buttons=(_dates_button(),),
    )


def _slot_back_button(session: Session, settings: Settings, slot_id: int) -> MenuButton:
    slot = session.get(Slot, slot_id)
    if slot is None:
        return _dates_button(label="Назад к датам")
    selected_date = _slot_local_date(slot, settings)
    return MenuButton(
        action=ClientMenuAction.SELECT_HAIRCUT_DATE,
        label="Назад ко времени",
        callback_data=client_callback_data(
            ClientMenuAction.SELECT_HAIRCUT_DATE,
            selected_date.isoformat(),
        ),
    )


def _reschedule_slot_back_button(
    session: Session,
    settings: Settings,
    slot_id: int,
) -> MenuButton:
    slot = session.get(Slot, slot_id)
    if slot is None:
        return _change_booking_button(label="Назад к датам")
    selected_date = _slot_local_date(slot, settings)
    return MenuButton(
        action=ClientMenuAction.SELECT_RESCHEDULE_DATE,
        label="Назад ко времени",
        callback_data=client_callback_data(
            ClientMenuAction.SELECT_RESCHEDULE_DATE,
            selected_date.isoformat(),
        ),
    )


def _format_slot_label(slot: Slot, settings: Settings) -> str:
    return _slot_local_start(slot, settings).strftime("%H:%M")


def _format_date_label(value: date) -> str:
    return (
        f"{_WEEKDAYS_SHORT_RU[value.weekday()]}, {value.day} {_MONTHS_RU[value.month]}"
    )


def _slot_local_date(slot: Slot, settings: Settings) -> date:
    return _slot_local_start(slot, settings).date()


def _slot_local_start(slot: Slot, settings: Settings) -> datetime:
    starts_at = slot.starts_at
    if starts_at.tzinfo is None:
        starts_at = starts_at.replace(tzinfo=settings.timezone_info)
    return starts_at.astimezone(settings.timezone_info)


def _contact_target(settings: Settings) -> str:
    return settings.stylist_contact_url


def _settings_location_line(place: str, settings: Settings) -> str:
    return format_location_line(place, **_settings_location_links(settings))


def _settings_location_links(settings: Settings) -> dict[str, str | None]:
    return {
        "yandex_map_url": settings.yandex_map_url,
        "google_map_url": settings.google_map_url,
        "default_map_url": settings.default_map_url,
    }


def _about_master_text() -> str:
    try:
        return ABOUT_MASTER_TEXT_PATH.read_text(encoding="utf-8").strip()
    except OSError:
        return (
            "Я Артём, мастер по цвету и форме. Работаю с вниманием к деталям, "
            "консультацией и рекомендациями по уходу."
        )


def _html_caption(text: str) -> str:
    return escape(text, quote=False)


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


def _require_active_booking_for_user(
    session: Session,
    *,
    telegram_user_id: int | None,
    now: datetime | None = None,
) -> Booking:
    if telegram_user_id is None:
        raise ClientIdentityRequired("Telegram user identity is required")

    booking = _active_booking_for_user(session, telegram_user_id, now=now)
    if booking is None:
        raise ClientActiveBookingRequired("Active booking is required")
    return booking


def _parse_slot_id(raw_value: str | None) -> int:
    if raw_value is None:
        raise ValueError("Missing slot ID")
    try:
        return int(raw_value)
    except ValueError as exc:
        raise ValueError("Invalid slot ID") from exc


def _parse_date(raw_value: str | None) -> date:
    if raw_value is None:
        raise ValueError("Missing date")
    try:
        return date.fromisoformat(raw_value)
    except ValueError as exc:
        raise ValueError("Invalid date") from exc


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

_WEEKDAYS_SHORT_RU = (
    "Пн",
    "Вт",
    "Ср",
    "Чт",
    "Пт",
    "Сб",
    "Вс",
)
