"""Client command and booking flow handlers."""

from __future__ import annotations

from collections.abc import Callable
from contextlib import AbstractAsyncContextManager, AbstractContextManager
from dataclasses import dataclass
from datetime import UTC, date, datetime
from decimal import Decimal
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
    admin_booking_client_lines,
    admin_new_booking_message,
    booking_cancelled_message,
    booking_confirmation_message,
    booking_rescheduled_message,
    format_location_line,
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
    ACTIVE_BOOKING_STATUSES,
    DEFAULT_HAIRCUT_DURATION_MINUTES,
    DEFAULT_HAIRCUT_SERVICE,
    HAIRCUT_FEMALE_SERVICE,
    HAIRCUT_MALE_SERVICE,
    HAIRCUT_SERVICES,
    SlotUnavailableError,
    cancel_booking_by_client,
    create_haircut_booking,
    haircut_price_for_service,
    haircut_service_label,
    list_available_slots,
    normalize_haircut_service,
    reschedule_booking_by_client,
)
from app.services.referrals import (
    REFERRAL_BONUS_THRESHOLD,
    build_referral_link,
    ensure_referral_code,
    referral_code_from_start_payload,
    referral_progress,
    register_referral_start,
)

CLIENT_WELCOME_TEXT = "\n".join(
    [
        "Привет!",
        "",
        "Здесь можно записаться на стрижку или написать по окрашиванию/консультации.",
        "",
        "Что хотите сделать?",
    ]
)
NO_AVAILABLE_SLOTS_TEXT = "Свободных дат пока нет."
HAIRCUT_SERVICE_CHOICE_TEXT = "Выберите тип стрижки."
HAIRCUT_DATE_LIST_TEXT = "Выберите дату для стрижки."
HAIRCUT_SLOT_LIST_TEXT = "Выберите время:"
HAIRCUT_CONFIRM_TEXT = "Подтвердить запись?"
NO_ACTIVE_BOOKING_TEXT = "У вас пока нет активной записи."
ACTIVE_BOOKING_HEADER_TEXT = "Ваша запись:"
ACTIVE_BOOKING_ACTION_TEXT = "Что хотите сделать?"
CHANGE_BOOKING_DATE_TEXT = "Выберите новую дату."
CANCEL_BOOKING_CONFIRM_TEXT = "Точно отменить эту запись?"
SLOT_UNAVAILABLE_TEXT = "Это время уже недоступно. Выберите другое."
HAIRCUT_DAILY_LIMIT_TEXT = (
    "На одну дату можно держать максимум 2 активные записи на стрижку. "
    "Если нужно больше времени подряд или особый формат, напишите мне."
)
IDENTITY_REQUIRED_TEXT = "Не удалось определить ваш Telegram-профиль."
UNKNOWN_ACTION_TEXT = "Неизвестное действие."
BOOKING_UNAVAILABLE_TEXT = "Запись временно недоступна."
REFERRAL_LINK_UNAVAILABLE_TEXT = (
    "Ссылка временно недоступна. Попробуйте позже или напишите мастеру."
)
PROJECT_ROOT = Path(__file__).resolve().parents[3]
ABOUT_MASTER_TEXT_PATH = PROJECT_ROOT / "about_me.md"
ABOUT_MASTER_PHOTO_PATH = PROJECT_ROOT / "IMG_9385.PNG"
MAX_ACTIVE_HAIRCUT_BOOKINGS_PER_DAY = 2
ADMIN_NEW_BOOKING_NOTIFICATION_KIND = "admin_new_booking"
ADMIN_BOOKING_RESCHEDULED_NOTIFICATION_KIND = "admin_booking_rescheduled"
ADMIN_BOOKING_CANCELLED_NOTIFICATION_KIND = "admin_booking_cancelled"
ADMIN_BOOKING_NOTIFICATION_KINDS = frozenset(
    {
        ADMIN_NEW_BOOKING_NOTIFICATION_KIND,
        ADMIN_BOOKING_RESCHEDULED_NOTIFICATION_KIND,
        ADMIN_BOOKING_CANCELLED_NOTIFICATION_KIND,
    }
)


class ClientIdentityRequired(ValueError):
    """Raised when a booking action has no Telegram user identity."""


class ClientActiveBookingRequired(ValueError):
    """Raised when a client action requires an active booking."""


class ClientDailyBookingLimitExceeded(ValueError):
    """Raised when a client tries to overbook one business day."""


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
    admin_notification_booking_id: int | None = None
    admin_notification_kind: str | None = None


@dataclass(frozen=True, slots=True)
class AdminBookingNotificationPayload:
    booking_id: int
    client_id: int
    kind: str
    text: str


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
    service: str | None = None,
    now: datetime | None = None,
) -> ClientMenuResponse:
    if service is None:
        return ClientMenuResponse(
            text=HAIRCUT_SERVICE_CHOICE_TEXT,
            buttons=_haircut_service_choice_buttons()
            + (_my_booking_button(), _main_menu_button()),
        )

    service = _parse_haircut_service(service)
    slots = tuple(list_available_slots(session, now=now))
    if not slots:
        return ClientMenuResponse(
            text=NO_AVAILABLE_SLOTS_TEXT,
            buttons=_haircut_service_choice_buttons()
            + (_my_booking_button(), _main_menu_button()),
        )

    return ClientMenuResponse(
        text=HAIRCUT_DATE_LIST_TEXT,
        buttons=_date_buttons(slots, settings, service=service)
        + (_my_booking_button(), _main_menu_button()),
    )


def handle_haircut_date_selection(
    session: Session,
    settings: Settings,
    *,
    selected_date: date,
    service: str = DEFAULT_HAIRCUT_SERVICE,
    now: datetime | None = None,
) -> SlotListResponse:
    service = _parse_haircut_service(service)
    slots = tuple(
        slot
        for slot in list_available_slots(session, now=now)
        if _slot_local_date(slot, settings) == selected_date
    )
    if not slots:
        return SlotListResponse(
            text=NO_AVAILABLE_SLOTS_TEXT,
            slots=(),
            buttons=(
                _dates_button(label="Назад к датам", service=service),
                _main_menu_button(),
            ),
        )

    return SlotListResponse(
        text=f"{HAIRCUT_SLOT_LIST_TEXT} {_format_date_label(selected_date)}",
        slots=tuple(_slot_option(slot, settings, service=service) for slot in slots),
        buttons=(
            _dates_button(label="Назад к датам", service=service),
            _my_booking_button(),
            _main_menu_button(),
        ),
    )


def handle_haircut_slot_selection(
    session: Session,
    settings: Settings,
    *,
    slot_id: int,
    service: str = DEFAULT_HAIRCUT_SERVICE,
    now: datetime | None = None,
) -> ClientTextResponse:
    service = _parse_haircut_service(service)
    slot = _require_available_slot(session, slot_id=slot_id, now=now)

    return ClientTextResponse(
        text=_slot_selection_text(
            title=HAIRCUT_CONFIRM_TEXT,
            service_label=haircut_service_label(service),
            slot=slot,
            settings=settings,
            duration_minutes=DEFAULT_HAIRCUT_DURATION_MINUTES,
            price_amount=haircut_price_for_service(service),
        )
    )


def handle_haircut_booking_confirmation(
    session: Session,
    settings: Settings,
    *,
    telegram_user_id: int | None,
    slot_id: int,
    service: str = DEFAULT_HAIRCUT_SERVICE,
    display_name: str | None = None,
    username: str | None = None,
    now: datetime | None = None,
) -> ClientBookingResponse:
    if telegram_user_id is None:
        raise ClientIdentityRequired("Telegram user identity is required")
    service = _parse_haircut_service(service)

    client = get_or_create_client(
        session,
        telegram_user_id=telegram_user_id,
        display_name=display_name,
        username=username,
    )
    _ensure_haircut_daily_limit(
        session,
        settings,
        client_id=client.id,
        slot_id=slot_id,
        now=now,
    )
    booking = create_haircut_booking(
        session,
        client_id=client.id,
        slot_id=slot_id,
        service=service,
    )
    return ClientBookingResponse(
        text=booking_confirmation_message(
            booking,
            timezone=settings.timezone_info,
            **_settings_location_links(settings),
        ),
        booking=booking,
        buttons=(
            _my_booking_button(),
            _referral_program_button(),
            _dates_button(label="Еще одна стрижка"),
            _main_menu_button(),
        ),
    )


def handle_referral_program_request(
    session: Session,
    settings: Settings,
    *,
    telegram_user_id: int | None,
    bot_username: str | None,
    display_name: str | None = None,
    username: str | None = None,
) -> ClientTextResponse:
    if telegram_user_id is None:
        raise ClientIdentityRequired("Telegram user identity is required")
    if not bot_username:
        return ClientTextResponse(
            text=REFERRAL_LINK_UNAVAILABLE_TEXT,
            buttons=(_contact_button(), _main_menu_button()),
        )

    client = get_or_create_client(
        session,
        telegram_user_id=telegram_user_id,
        display_name=display_name,
        username=username,
    )
    code = ensure_referral_code(session, client_id=client.id)
    progress = referral_progress(session, client_id=client.id)
    link = build_referral_link(bot_username=bot_username, code=code.code)

    return ClientTextResponse(
        text="\n".join(
            [
                "Ваша ссылка для рекомендаций:",
                link,
                "",
                f"За {REFERRAL_BONUS_THRESHOLD} новых клиентов, которые пришли "
                "по вашей ссылке и дошли до визита, я подарю вам "
                "классную профессиональную косметику для волос: уход или стайлинг.",
                "",
                f"Засчитано: {progress.qualified_count} из {REFERRAL_BONUS_THRESHOLD}",
                f"Ожидают визита: {progress.pending_count}",
                f"Бонусов к выдаче: {progress.pending_bonus_count}",
            ]
        ),
        buttons=(
            _my_booking_button(),
            _dates_button(label="Стрижка"),
            _main_menu_button(),
        ),
    )


def handle_start_payload(
    session: Session,
    settings: Settings,
    *,
    telegram_user_id: int | None,
    display_name: str | None = None,
    username: str | None = None,
    start_payload: str | None = None,
    now: datetime | None = None,
) -> ClientCallbackResponse:
    referral_code = referral_code_from_start_payload(start_payload)
    referral_registered = False
    if referral_code and telegram_user_id is not None:
        client = get_or_create_client(
            session,
            telegram_user_id=telegram_user_id,
            display_name=display_name,
            username=username,
        )
        registration = register_referral_start(
            session,
            referral_code=referral_code,
            referred_client_id=client.id,
        )
        referral_registered = registration.registered

    response = handle_start_command(settings)
    text = response.text
    if referral_registered:
        text = "Рекомендация сохранена.\n\n" + text
    return ClientCallbackResponse(
        text=text,
        buttons=response.buttons,
        should_commit=referral_registered,
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
        buttons=_service_choice_buttons(),
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
        buttons=(
            _my_booking_button(),
            _dates_button(label="Еще одна стрижка"),
            _main_menu_button(),
        ),
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
    bot_username: str | None = None,
    start_payload: str | None = None,
) -> ClientCallbackResponse:
    try:
        parsed = parse_client_callback_data(callback_payload)
    except ValueError:
        return ClientCallbackResponse(text=UNKNOWN_ACTION_TEXT)

    if parsed.action == ClientMenuAction.MENU:
        response = handle_start_command(settings)
        return ClientCallbackResponse(text=response.text, buttons=response.buttons)

    if parsed.action == ClientMenuAction.COMPLEX_SERVICE:
        response = handle_complex_service_redirect(settings)
        return ClientCallbackResponse(
            text=response.text,
            buttons=response.buttons,
            should_commit=_ensure_client_record_for_contact(
                session,
                telegram_user_id=telegram_user_id,
                display_name=display_name,
                username=username,
            ),
        )

    if parsed.action == ClientMenuAction.CONSULTATION:
        response = handle_consultation_redirect(settings)
        return ClientCallbackResponse(
            text=response.text,
            buttons=response.buttons,
            should_commit=_ensure_client_record_for_contact(
                session,
                telegram_user_id=telegram_user_id,
                display_name=display_name,
                username=username,
            ),
        )

    if parsed.action == ClientMenuAction.ABOUT_MASTER:
        response = handle_about_master_request()
        return ClientCallbackResponse(text=response.text, buttons=response.buttons)

    if parsed.action == ClientMenuAction.CONTACT:
        response = handle_contact_request(settings)
        return ClientCallbackResponse(
            text=response.text,
            buttons=response.buttons,
            should_commit=_ensure_client_record_for_contact(
                session,
                telegram_user_id=telegram_user_id,
                display_name=display_name,
                username=username,
            ),
        )

    if session is None:
        return ClientCallbackResponse(text=BOOKING_UNAVAILABLE_TEXT)

    if parsed.action == ClientMenuAction.REFERRAL_PROGRAM:
        try:
            response = handle_referral_program_request(
                session,
                settings,
                telegram_user_id=telegram_user_id,
                bot_username=bot_username,
                display_name=display_name,
                username=username,
            )
        except ClientIdentityRequired:
            return ClientCallbackResponse(text=IDENTITY_REQUIRED_TEXT)
        return ClientCallbackResponse(
            text=response.text,
            buttons=response.buttons,
            should_commit=True,
        )

    if parsed.action == ClientMenuAction.BOOK_HAIRCUT:
        try:
            service = _parse_haircut_service(parsed.value) if parsed.value else None
        except ValueError:
            return ClientCallbackResponse(text=UNKNOWN_ACTION_TEXT)
        response = handle_haircut_booking_start(
            session,
            settings,
            service=service,
            now=now,
        )
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
            return _slot_unavailable_reschedule_response(
                session,
                settings,
                telegram_user_id=telegram_user_id,
                now=now,
            )
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
            return _slot_unavailable_reschedule_response(
                session,
                settings,
                telegram_user_id=telegram_user_id,
                now=now,
            )
        return ClientCallbackResponse(
            text=response.text,
            buttons=response.buttons,
            should_commit=True,
            admin_notification_booking_id=response.booking.id,
            admin_notification_kind=ADMIN_BOOKING_RESCHEDULED_NOTIFICATION_KIND,
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
            admin_notification_booking_id=response.booking.id,
            admin_notification_kind=ADMIN_BOOKING_CANCELLED_NOTIFICATION_KIND,
        )

    if parsed.action == ClientMenuAction.SELECT_HAIRCUT_DATE:
        try:
            service, selected_date = _parse_haircut_date_value(parsed.value)
        except ValueError:
            return ClientCallbackResponse(text=UNKNOWN_ACTION_TEXT)
        response = handle_haircut_date_selection(
            session,
            settings,
            selected_date=selected_date,
            service=service,
            now=now,
        )
        return ClientCallbackResponse(
            text=response.text,
            slots=response.slots,
            buttons=response.buttons,
        )

    if parsed.action == ClientMenuAction.SELECT_HAIRCUT_SLOT:
        try:
            service, slot_id = _parse_haircut_slot_value(parsed.value)
        except ValueError:
            return ClientCallbackResponse(text=UNKNOWN_ACTION_TEXT)
        try:
            response = handle_haircut_slot_selection(
                session,
                settings,
                slot_id=slot_id,
                service=service,
                now=now,
            )
        except SlotUnavailableError:
            return _slot_unavailable_haircut_response(
                session,
                settings,
                service=service,
                now=now,
            )

        return ClientCallbackResponse(
            text=response.text,
            buttons=(
                MenuButton(
                    action=ClientMenuAction.CONFIRM_HAIRCUT,
                    label="Подтвердить запись",
                    callback_data=client_callback_data(
                        ClientMenuAction.CONFIRM_HAIRCUT,
                        _haircut_slot_value(service, slot_id),
                    ),
                ),
                _slot_back_button(session, settings, slot_id, service=service),
                _main_menu_button(),
            ),
        )

    if parsed.action == ClientMenuAction.CONFIRM_HAIRCUT:
        try:
            service, slot_id = _parse_haircut_slot_value(parsed.value)
            response = handle_haircut_booking_confirmation(
                session,
                settings,
                telegram_user_id=telegram_user_id,
                slot_id=slot_id,
                service=service,
                display_name=display_name,
                username=username,
                now=now,
            )
        except SlotUnavailableError:
            return _slot_unavailable_haircut_response(
                session,
                settings,
                service=service,
                now=now,
            )
        except ClientIdentityRequired:
            return ClientCallbackResponse(text=IDENTITY_REQUIRED_TEXT)
        except ClientDailyBookingLimitExceeded:
            return ClientCallbackResponse(
                text=HAIRCUT_DAILY_LIMIT_TEXT,
                buttons=(
                    _dates_button(label="Другие даты", service=service),
                    _contact_button(label="Написать"),
                    _main_menu_button(),
                ),
            )
        except ValueError:
            return ClientCallbackResponse(text=UNKNOWN_ACTION_TEXT)
        return ClientCallbackResponse(
            text=response.text,
            buttons=response.buttons,
            should_commit=True,
            admin_notification_booking_id=response.booking.id,
            admin_notification_kind=ADMIN_NEW_BOOKING_NOTIFICATION_KIND,
        )

    return ClientCallbackResponse(text=UNKNOWN_ACTION_TEXT)


def handle_complex_service_redirect(settings: Settings) -> ClientTextResponse:
    contact = _contact_target(settings)
    return ClientTextResponse(
        text="\n".join(
            [
                "Окрашивание требует консультации.",
                f"Напишите мне в чат: {contact}",
                "Я уточню длительность, сложность и сам внесу запись.",
            ]
        ),
        buttons=_service_choice_buttons(include_complex=False),
    )


def handle_consultation_redirect(settings: Settings) -> ClientTextResponse:
    return ClientTextResponse(
        text="\n".join(
            [
                "Для консультации напишите мне в чат.",
                _contact_target(settings),
            ]
        ),
        buttons=_service_choice_buttons(include_consultation=False),
    )


def handle_about_master_request() -> ClientTextResponse:
    return ClientTextResponse(
        text=_about_master_text(),
        buttons=_service_choice_buttons(include_my_booking=True),
    )


def handle_contact_request(settings: Settings) -> ClientTextResponse:
    return ClientTextResponse(
        text=f"Связаться со стилистом: {_contact_target(settings)}",
        buttons=_service_choice_buttons(include_my_booking=True),
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
            buttons=_service_choice_buttons(),
        )

    booking_text = booking_confirmation_message(
        booking,
        timezone=settings.timezone_info,
        include_change_hint=False,
        **_settings_location_links(settings),
    ).replace("Запись подтверждена\n\n", "")
    return ClientTextResponse(
        text="\n".join(
            [
                ACTIVE_BOOKING_HEADER_TEXT,
                "",
                booking_text,
                "",
                ACTIVE_BOOKING_ACTION_TEXT,
            ]
        ),
        buttons=(
            _change_booking_button(),
            _cancel_booking_button(),
            _referral_program_button(),
            _dates_button(label="Еще одна стрижка"),
            _main_menu_button(),
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
            buttons=(_my_booking_button(), _main_menu_button()),
        )
    return ClientMenuResponse(
        text=CHANGE_BOOKING_DATE_TEXT,
        buttons=_date_buttons(
            slots,
            settings,
            action=ClientMenuAction.SELECT_RESCHEDULE_DATE,
        )
        + (_my_booking_button(label="Назад к моей записи"), _main_menu_button()),
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
            buttons=(
                _change_booking_button(label="Назад к датам"),
                _my_booking_button(),
                _main_menu_button(),
            ),
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
            _main_menu_button(),
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
    booking = _require_active_booking_for_user(
        session,
        telegram_user_id=telegram_user_id,
        now=now,
    )
    slot = _require_available_slot(session, slot_id=slot_id, now=now)
    return ClientTextResponse(
        text=_slot_selection_text(
            title="Подтвердить новое время?",
            service_label=haircut_service_label(booking.service),
            slot=slot,
            settings=settings,
            duration_minutes=booking.duration_minutes,
            price_amount=booking.price_amount,
        ),
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
            _main_menu_button(),
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
        ),
        buttons=(_my_booking_button(), _main_menu_button()),
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


def _ensure_client_record_for_contact(
    session: Session | None,
    *,
    telegram_user_id: int | None,
    display_name: str | None = None,
    username: str | None = None,
) -> bool:
    if session is None or telegram_user_id is None:
        return False
    get_or_create_client(
        session,
        telegram_user_id=telegram_user_id,
        display_name=display_name,
        username=username,
    )
    return True


def _admin_booking_notification_payload(
    session: Session,
    settings: Settings,
    *,
    booking_id: int,
    kind: str,
) -> AdminBookingNotificationPayload | None:
    if kind not in ADMIN_BOOKING_NOTIFICATION_KINDS:
        raise ValueError("Unknown admin booking notification kind")

    booking = session.get(Booking, booking_id)
    if booking is None or booking.id is None:
        return None

    return AdminBookingNotificationPayload(
        booking_id=booking.id,
        client_id=booking.client_id,
        kind=kind,
        text=_admin_booking_notification_text(booking, settings, kind=kind),
    )


def _admin_booking_notification_text(
    booking: Booking,
    settings: Settings,
    *,
    kind: str,
) -> str:
    if kind == ADMIN_NEW_BOOKING_NOTIFICATION_KIND:
        return admin_new_booking_message(
            booking,
            timezone=settings.timezone_info,
            **_settings_location_links(settings),
        )
    if kind == ADMIN_BOOKING_RESCHEDULED_NOTIFICATION_KIND:
        return "\n".join(
            [
                "Клиент перенес запись",
                *admin_booking_client_lines(booking),
                "",
                booking_rescheduled_message(
                    booking,
                    timezone=settings.timezone_info,
                    **_settings_location_links(settings),
                ),
            ]
        )
    if kind == ADMIN_BOOKING_CANCELLED_NOTIFICATION_KIND:
        return "\n".join(
            [
                "Клиент отменил запись",
                *admin_booking_client_lines(booking),
                "",
                booking_cancelled_message(
                    booking,
                    reason="отменено клиентом",
                    timezone=settings.timezone_info,
                    **_settings_location_links(settings),
                ),
            ]
        )
    raise ValueError("Unknown admin booking notification kind")


def _record_admin_booking_notification(
    session: Session,
    *,
    payload: AdminBookingNotificationPayload,
    recipient_telegram_id: int,
    status: DeliveryStatus,
    error: str | None,
    sent_at: datetime | None,
) -> None:
    session.add(
        NotificationLog(
            booking_id=payload.booking_id,
            client_id=payload.client_id,
            kind=payload.kind,
            recipient_telegram_id=recipient_telegram_id,
            status=status,
            error=error,
            sent_at=sent_at,
        )
    )
    session.flush()


async def dispatch_client_callback_async(
    async_session_factory: async_sessionmaker[AsyncSession],
    settings: Settings,
    *,
    callback_payload: str | None,
    telegram_user_id: int | None,
    display_name: str | None = None,
    username: str | None = None,
    now: datetime | None = None,
    bot_username: str | None = None,
    start_payload: str | None = None,
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
                bot_username=bot_username,
                start_payload=start_payload,
            )
        )
        if response.should_commit:
            await async_session.commit()
        else:
            await async_session.rollback()
        return response


async def notify_admins_about_booking_event(
    async_session_factory: Callable[
        [],
        AbstractAsyncContextManager[AsyncSession],
    ],
    settings: Settings,
    *,
    bot,
    booking_id: int | None,
    kind: str | None,
) -> None:
    if booking_id is None or kind is None:
        return

    async with async_session_factory() as async_session:
        payload = await async_session.run_sync(
            lambda session: _admin_booking_notification_payload(
                session,
                settings,
                booking_id=booking_id,
                kind=kind,
            )
        )
        if payload is None:
            await async_session.rollback()
            return

        for admin_telegram_id in settings.admin_telegram_ids:
            status = DeliveryStatus.PENDING
            error = None
            sent_at = None
            try:
                await bot.send_message(admin_telegram_id, payload.text)
            except Exception as exc:  # noqa: BLE001 - delivery failures are logged
                status = DeliveryStatus.FAILED
                error = str(exc) or exc.__class__.__name__
            else:
                status = DeliveryStatus.SENT
                sent_at = datetime.now(UTC)

            def record_notification(
                session: Session,
                *,
                admin_telegram_id: int = admin_telegram_id,
                status: DeliveryStatus = status,
                error: str | None = error,
                sent_at: datetime | None = sent_at,
            ) -> None:
                _record_admin_booking_notification(
                    session,
                    payload=payload,
                    recipient_telegram_id=admin_telegram_id,
                    status=status,
                    error=error,
                    sent_at=sent_at,
                )

            await async_session.run_sync(record_notification)

        await async_session.commit()


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
    resolved_bot_username: str | None = None

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

        start_payload = _start_payload(message.text)
        response = await _dispatch_start_payload(
            telegram_user_id=message.from_user.id if message.from_user else None,
            display_name=message.from_user.full_name if message.from_user else None,
            username=message.from_user.username if message.from_user else None,
            start_payload=start_payload,
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
        if async_session_factory is not None:
            await notify_admins_about_booking_event(
                async_session_factory,
                settings,
                bot=callback.bot,
                booking_id=response.admin_notification_booking_id,
                kind=response.admin_notification_kind,
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
        kwargs = _callback_kwargs(callback)
        kwargs["bot_username"] = await _bot_username(callback.bot)
        return await _dispatch_payload(**kwargs)

    async def _bot_username(bot) -> str | None:
        nonlocal resolved_bot_username
        if resolved_bot_username:
            return resolved_bot_username
        try:
            me = await bot.get_me()
        except Exception:  # noqa: BLE001 - referral link can degrade gracefully
            return None
        resolved_bot_username = me.username
        return resolved_bot_username

    async def _dispatch_start_payload(**kwargs: object) -> ClientCallbackResponse:
        if async_session_factory is not None:
            async with async_session_factory() as async_session:
                response = await async_session.run_sync(
                    lambda sync_session: handle_start_payload(
                        sync_session,
                        settings,
                        **kwargs,
                    )
                )
                if response.should_commit:
                    await async_session.commit()
                else:
                    await async_session.rollback()
                return response

        if session_factory is not None:
            with session_factory() as session:
                response = handle_start_payload(session, settings, **kwargs)
                if response.should_commit:
                    session.commit()
                else:
                    session.rollback()
                return response

        response = handle_start_command(settings)
        return ClientCallbackResponse(text=response.text, buttons=response.buttons)

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


def _start_payload(message_text: str | None) -> str | None:
    if not message_text:
        return None
    parts = message_text.strip().split(maxsplit=1)
    if len(parts) != 2:
        return None
    if not parts[0].startswith("/start"):
        return None
    return parts[1].strip() or None


def _slot_option(
    slot: Slot,
    settings: Settings,
    *,
    action: ClientMenuAction = ClientMenuAction.SELECT_HAIRCUT_SLOT,
    service: str | None = None,
) -> SlotOption:
    if slot.id is None:
        raise ValueError("Slot must be flushed before it can be rendered")
    value: str | int = slot.id
    if service is not None and action == ClientMenuAction.SELECT_HAIRCUT_SLOT:
        value = _haircut_slot_value(service, slot.id)
    return SlotOption(
        slot_id=slot.id,
        label=_format_slot_label(slot, settings),
        callback_data=client_callback_data(
            action,
            value,
        ),
    )


def _date_buttons(
    slots: tuple[Slot, ...],
    settings: Settings,
    *,
    action: ClientMenuAction = ClientMenuAction.SELECT_HAIRCUT_DATE,
    service: str | None = None,
) -> tuple[MenuButton, ...]:
    dates = sorted({_slot_local_date(slot, settings) for slot in slots})
    return tuple(
        MenuButton(
            action=action,
            label=_format_date_label(value),
            callback_data=client_callback_data(
                action,
                _haircut_date_value(service, value)
                if service is not None
                and action == ClientMenuAction.SELECT_HAIRCUT_DATE
                else value.isoformat(),
            ),
        )
        for value in dates
    )


def _dates_button(
    *,
    label: str = "Стрижка",
    service: str | None = None,
) -> MenuButton:
    return MenuButton(
        action=ClientMenuAction.BOOK_HAIRCUT,
        label=label,
        callback_data=client_callback_data(ClientMenuAction.BOOK_HAIRCUT, service)
        if service is not None
        else client_callback_data(ClientMenuAction.BOOK_HAIRCUT),
    )


def _main_menu_button(*, label: str = "Главное меню") -> MenuButton:
    return MenuButton(
        action=ClientMenuAction.MENU,
        label=label,
        callback_data=client_callback_data(ClientMenuAction.MENU),
    )


def _my_booking_button(*, label: str = "Моя запись") -> MenuButton:
    return MenuButton(
        action=ClientMenuAction.MY_BOOKING,
        label=label,
        callback_data=client_callback_data(ClientMenuAction.MY_BOOKING),
    )


def _complex_service_button(*, label: str = "Окрашивание") -> MenuButton:
    return MenuButton(
        action=ClientMenuAction.COMPLEX_SERVICE,
        label=label,
        callback_data=client_callback_data(ClientMenuAction.COMPLEX_SERVICE),
    )


def _consultation_button(*, label: str = "Консультация") -> MenuButton:
    return MenuButton(
        action=ClientMenuAction.CONSULTATION,
        label=label,
        callback_data=client_callback_data(ClientMenuAction.CONSULTATION),
    )


def _contact_button(*, label: str = "Связаться") -> MenuButton:
    return MenuButton(
        action=ClientMenuAction.CONTACT,
        label=label,
        callback_data=client_callback_data(ClientMenuAction.CONTACT),
    )


def _referral_program_button(*, label: str = "Рекомендации") -> MenuButton:
    return MenuButton(
        action=ClientMenuAction.REFERRAL_PROGRAM,
        label=label,
        callback_data=client_callback_data(ClientMenuAction.REFERRAL_PROGRAM),
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


def _service_choice_buttons(
    *,
    include_haircut: bool = True,
    include_complex: bool = True,
    include_consultation: bool = True,
    include_my_booking: bool = False,
    include_main_menu: bool = True,
) -> tuple[MenuButton, ...]:
    buttons: list[MenuButton] = []
    if include_haircut:
        buttons.append(_dates_button(label="Стрижка"))
    if include_complex:
        buttons.append(_complex_service_button())
    if include_consultation:
        buttons.append(_consultation_button())
    if include_my_booking:
        buttons.append(_my_booking_button())
    if include_main_menu:
        buttons.append(_main_menu_button())
    return tuple(buttons)


def _haircut_service_choice_buttons() -> tuple[MenuButton, ...]:
    return (
        _dates_button(
            label=f"Мужская стрижка - {_haircut_price_label(HAIRCUT_MALE_SERVICE)} GEL",
            service=HAIRCUT_MALE_SERVICE,
        ),
        _dates_button(
            label=(
                f"Женская стрижка - {_haircut_price_label(HAIRCUT_FEMALE_SERVICE)} GEL"
            ),
            service=HAIRCUT_FEMALE_SERVICE,
        ),
    )


def _no_active_booking_response() -> ClientCallbackResponse:
    return ClientCallbackResponse(
        text=NO_ACTIVE_BOOKING_TEXT,
        buttons=_service_choice_buttons(),
    )


def _slot_unavailable_haircut_response(
    session: Session,
    settings: Settings,
    *,
    service: str = DEFAULT_HAIRCUT_SERVICE,
    now: datetime | None = None,
) -> ClientCallbackResponse:
    response = handle_haircut_booking_start(
        session,
        settings,
        service=service,
        now=now,
    )
    return ClientCallbackResponse(
        text=_append_recovery_text(SLOT_UNAVAILABLE_TEXT, response.text),
        buttons=response.buttons,
    )


def _slot_unavailable_reschedule_response(
    session: Session,
    settings: Settings,
    *,
    telegram_user_id: int | None,
    now: datetime | None = None,
) -> ClientCallbackResponse:
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

    return ClientCallbackResponse(
        text=_append_recovery_text(SLOT_UNAVAILABLE_TEXT, response.text),
        buttons=response.buttons,
    )


def _append_recovery_text(primary: str, recovery: str) -> str:
    if not recovery:
        return primary
    return f"{primary}\n\n{recovery}"


def _slot_back_button(
    session: Session,
    settings: Settings,
    slot_id: int,
    *,
    service: str = DEFAULT_HAIRCUT_SERVICE,
) -> MenuButton:
    slot = session.get(Slot, slot_id)
    if slot is None:
        return _dates_button(label="Назад к датам", service=service)
    selected_date = _slot_local_date(slot, settings)
    return MenuButton(
        action=ClientMenuAction.SELECT_HAIRCUT_DATE,
        label="Назад ко времени",
        callback_data=client_callback_data(
            ClientMenuAction.SELECT_HAIRCUT_DATE,
            _haircut_date_value(service, selected_date),
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
    return _datetime_local(slot.starts_at, settings)


def _booking_local_date(booking: Booking, settings: Settings) -> date:
    return _booking_local_start(booking, settings).date()


def _booking_local_start(booking: Booking, settings: Settings) -> datetime:
    return _datetime_local(booking.starts_at, settings)


def _datetime_local(value: datetime, settings: Settings) -> datetime:
    if value.tzinfo is None:
        value = value.replace(tzinfo=settings.timezone_info)
    return value.astimezone(settings.timezone_info)


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


def _require_available_slot(
    session: Session,
    *,
    slot_id: int,
    now: datetime | None = None,
) -> Slot:
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
    return slot


def _slot_selection_text(
    *,
    title: str,
    service_label: str,
    slot: Slot,
    settings: Settings,
    duration_minutes: int,
    price_amount: Decimal,
) -> str:
    return "\n".join(
        [
            title,
            service_label,
            f"Время: {_format_slot_label(slot, settings)}",
            _settings_location_line(slot.place, settings),
            f"Длительность: {duration_minutes} мин",
            f"Цена: {_format_money(price_amount)} GEL",
        ]
    )


def _format_money(value: Decimal) -> str:
    return f"{value:.2f}".rstrip("0").rstrip(".")


def _haircut_price_label(service: str) -> str:
    return _format_money(haircut_price_for_service(service))


def _parse_haircut_service(raw_value: str) -> str:
    try:
        return normalize_haircut_service(raw_value)
    except ValueError as exc:
        raise ValueError("Invalid haircut service") from exc


def _haircut_date_value(service: str, selected_date: date) -> str:
    return f"{_parse_haircut_service(service)}|{selected_date.isoformat()}"


def _haircut_slot_value(service: str, slot_id: int) -> str:
    return f"{_parse_haircut_service(service)}|{slot_id}"


def _ensure_haircut_daily_limit(
    session: Session,
    settings: Settings,
    *,
    client_id: int,
    slot_id: int,
    now: datetime | None = None,
) -> None:
    slot = session.get(Slot, slot_id)
    if slot is None:
        raise SlotUnavailableError(f"Slot is unavailable: {slot_id}")

    target_date = _slot_local_date(slot, settings)
    cutoff = _datetime_local(now or datetime.now(UTC), settings)
    active_haircuts = tuple(
        session.scalars(
            select(Booking).where(
                Booking.client_id == client_id,
                Booking.service.in_(HAIRCUT_SERVICES),
                Booking.status.in_(ACTIVE_BOOKING_STATUSES),
            )
        )
    )
    same_day_count = sum(
        1
        for booking in active_haircuts
        if _booking_local_date(booking, settings) == target_date
        and _booking_local_start(booking, settings) > cutoff
    )
    if same_day_count >= MAX_ACTIVE_HAIRCUT_BOOKINGS_PER_DAY:
        raise ClientDailyBookingLimitExceeded("client haircut daily limit exceeded")


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


def _parse_haircut_slot_value(raw_value: str | None) -> tuple[str, int]:
    if raw_value is None:
        raise ValueError("Missing slot ID")
    if "|" not in raw_value:
        return DEFAULT_HAIRCUT_SERVICE, _parse_slot_id(raw_value)
    raw_service, raw_slot_id = raw_value.split("|", maxsplit=1)
    return _parse_haircut_service(raw_service), _parse_slot_id(raw_slot_id)


def _parse_date(raw_value: str | None) -> date:
    if raw_value is None:
        raise ValueError("Missing date")
    try:
        return date.fromisoformat(raw_value)
    except ValueError as exc:
        raise ValueError("Invalid date") from exc


def _parse_haircut_date_value(raw_value: str | None) -> tuple[str, date]:
    if raw_value is None:
        raise ValueError("Missing date")
    if "|" not in raw_value:
        return DEFAULT_HAIRCUT_SERVICE, _parse_date(raw_value)
    raw_service, raw_date = raw_value.split("|", maxsplit=1)
    return _parse_haircut_service(raw_service), _parse_date(raw_date)


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
