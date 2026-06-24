"""Reusable bot menu definitions."""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum

ADMIN_CALLBACK_PREFIX = "admin"
CLIENT_CALLBACK_PREFIX = "client"


class AdminMenuAction(StrEnum):
    MENU = "menu"
    TODAY = "today"
    THIS_WEEK = "this_week"
    MANUAL_BOOKING = "manual_booking"
    CHANGE_BOOKING = "change_booking"
    CANCEL_BOOKING = "cancel_booking"
    REVENUE = "revenue"
    CLIENTS = "clients"
    CLIENT_CARD = "client_card"
    CONTACT_CLIENT = "contact_client"
    REFERRAL_BONUSES = "referral_bonuses"
    MARK_REFERRAL_BONUS_AWARDED = "mark_referral_bonus_awarded"
    SCHEDULE_DATE = "schedule_date"
    BOOKING_DETAIL = "booking_detail"
    RESCHEDULE_DATE = "reschedule_date"
    RESCHEDULE_SLOT = "reschedule_slot"
    CONFIRM_RESCHEDULE = "confirm_reschedule"
    CONFIRM_CANCEL = "confirm_cancel"


class ClientMenuAction(StrEnum):
    BOOK_HAIRCUT = "book_haircut"
    COMPLEX_SERVICE = "complex_service"
    ABOUT_MASTER = "about_master"
    REFERRAL_PROGRAM = "referral_program"
    MY_BOOKING = "my_booking"
    RESCHEDULE_CANCEL = "reschedule_cancel"
    CONTACT = "contact"
    SELECT_HAIRCUT_DATE = "select_haircut_date"
    SELECT_HAIRCUT_SLOT = "select_haircut_slot"
    CONFIRM_HAIRCUT = "confirm_haircut"
    CHANGE_BOOKING = "change_booking"
    SELECT_RESCHEDULE_DATE = "select_reschedule_date"
    SELECT_RESCHEDULE_SLOT = "select_reschedule_slot"
    CONFIRM_RESCHEDULE = "confirm_reschedule"
    CANCEL_BOOKING = "cancel_booking"
    CONFIRM_CANCEL = "confirm_cancel"


@dataclass(frozen=True, slots=True)
class ClientCallbackData:
    action: ClientMenuAction
    value: str | None = None


@dataclass(frozen=True, slots=True)
class MenuButton:
    action: AdminMenuAction | ClientMenuAction
    label: str
    callback_data: str


_ADMIN_MENU_LAYOUT: tuple[tuple[AdminMenuAction, str], ...] = (
    (AdminMenuAction.TODAY, "Сегодня"),
    (AdminMenuAction.THIS_WEEK, "Ближайшие даты"),
    (AdminMenuAction.MANUAL_BOOKING, "Создать запись"),
    (AdminMenuAction.CHANGE_BOOKING, "Перенести запись"),
    (AdminMenuAction.CANCEL_BOOKING, "Отменить запись"),
    (AdminMenuAction.REVENUE, "Выручка"),
    (AdminMenuAction.CLIENTS, "Клиенты"),
    (AdminMenuAction.REFERRAL_BONUSES, "Бонусы"),
)

_CLIENT_MENU_LAYOUT: tuple[tuple[ClientMenuAction, str], ...] = (
    (ClientMenuAction.BOOK_HAIRCUT, "Записаться"),
    (ClientMenuAction.COMPLEX_SERVICE, "Окрашивание / сложная услуга"),
    (ClientMenuAction.ABOUT_MASTER, "О мастере"),
    (ClientMenuAction.REFERRAL_PROGRAM, "Рекомендации"),
    (ClientMenuAction.MY_BOOKING, "Моя запись"),
    (ClientMenuAction.RESCHEDULE_CANCEL, "Перенести / отменить"),
    (ClientMenuAction.CONTACT, "Связаться"),
)


def admin_menu_actions() -> tuple[AdminMenuAction, ...]:
    return tuple(action for action, _label in _ADMIN_MENU_LAYOUT)


def admin_callback_data(action: AdminMenuAction, value: str | int | None = None) -> str:
    if value is not None:
        return f"{ADMIN_CALLBACK_PREFIX}:{action.value}:{value}"
    return f"{ADMIN_CALLBACK_PREFIX}:{action.value}"


def parse_admin_callback_data(payload: str | None) -> AdminMenuAction:
    if not isinstance(payload, str):
        raise ValueError("Missing admin callback payload")

    prefix, separator, raw_action = payload.partition(":")
    if prefix != ADMIN_CALLBACK_PREFIX or not separator or not raw_action:
        raise ValueError("Not an admin callback payload")

    try:
        return AdminMenuAction(raw_action)
    except ValueError as exc:
        raise ValueError("Unknown admin action") from exc


def admin_menu_buttons() -> tuple[MenuButton, ...]:
    return tuple(
        MenuButton(
            action=action,
            label=label,
            callback_data=admin_callback_data(action),
        )
        for action, label in _ADMIN_MENU_LAYOUT
    )


def client_menu_actions() -> tuple[ClientMenuAction, ...]:
    return tuple(action for action, _label in _CLIENT_MENU_LAYOUT)


def client_callback_data(
    action: ClientMenuAction,
    value: str | int | None = None,
) -> str:
    if value is None:
        return f"{CLIENT_CALLBACK_PREFIX}:{action.value}"
    return f"{CLIENT_CALLBACK_PREFIX}:{action.value}:{value}"


def parse_client_callback_data(payload: str | None) -> ClientCallbackData:
    if not isinstance(payload, str):
        raise ValueError("Missing client callback payload")

    prefix, separator, remainder = payload.partition(":")
    if prefix != CLIENT_CALLBACK_PREFIX or not separator or not remainder:
        raise ValueError("Not a client callback payload")

    raw_action, value_separator, raw_value = remainder.partition(":")
    try:
        action = ClientMenuAction(raw_action)
    except ValueError as exc:
        raise ValueError("Unknown client action") from exc

    value = raw_value if value_separator else None
    return ClientCallbackData(action=action, value=value)


def client_menu_buttons() -> tuple[MenuButton, ...]:
    return tuple(
        MenuButton(
            action=action,
            label=label,
            callback_data=client_callback_data(action),
        )
        for action, label in _CLIENT_MENU_LAYOUT
    )
