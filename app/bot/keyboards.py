"""Reusable bot menu definitions."""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum

ADMIN_CALLBACK_PREFIX = "admin"


class AdminMenuAction(StrEnum):
    TODAY = "today"
    THIS_WEEK = "this_week"
    MANUAL_BOOKING = "manual_booking"
    CHANGE_BOOKING = "change_booking"
    CANCEL_BOOKING = "cancel_booking"
    REVENUE = "revenue"
    CLIENTS = "clients"


@dataclass(frozen=True, slots=True)
class MenuButton:
    action: AdminMenuAction
    label: str
    callback_data: str


_ADMIN_MENU_LAYOUT: tuple[tuple[AdminMenuAction, str], ...] = (
    (AdminMenuAction.TODAY, "Today"),
    (AdminMenuAction.THIS_WEEK, "This week"),
    (AdminMenuAction.MANUAL_BOOKING, "Manual booking"),
    (AdminMenuAction.CHANGE_BOOKING, "Change booking"),
    (AdminMenuAction.CANCEL_BOOKING, "Cancel booking"),
    (AdminMenuAction.REVENUE, "Revenue"),
    (AdminMenuAction.CLIENTS, "Clients"),
)


def admin_menu_actions() -> tuple[AdminMenuAction, ...]:
    return tuple(action for action, _label in _ADMIN_MENU_LAYOUT)


def admin_callback_data(action: AdminMenuAction) -> str:
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
