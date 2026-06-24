import pytest

from app.bot.handlers.admin import (
    ADMIN_MENU_TEXT,
    AdminAccessDenied,
    build_admin_menu_response,
    build_admin_router,
    handle_admin_callback,
    handle_admin_menu_command,
    is_admin_user,
    resolve_admin_action,
)
from app.bot.handlers.client import CLIENT_WELCOME_TEXT, handle_start_command
from app.bot.keyboards import AdminMenuAction, admin_callback_data, admin_menu_actions
from app.config import Settings


def test_admin_allowlist_required() -> None:
    settings = _settings()

    assert is_admin_user(111, settings)
    assert is_admin_user(222, settings)
    assert not is_admin_user(333, settings)
    assert not is_admin_user(None, settings)

    response = handle_admin_menu_command(111, settings)
    assert response.text == ADMIN_MENU_TEXT
    assert response.buttons

    with pytest.raises(AdminAccessDenied):
        handle_admin_menu_command(333, settings)

    with pytest.raises(AdminAccessDenied):
        handle_admin_callback(
            333,
            settings,
            admin_callback_data(AdminMenuAction.REVENUE),
        )

    response = handle_admin_callback(
        222,
        settings,
        admin_callback_data(AdminMenuAction.REVENUE),
    )
    assert response.action is AdminMenuAction.REVENUE
    assert (
        resolve_admin_action(
            222,
            settings,
            admin_callback_data(AdminMenuAction.REVENUE),
        )
        is AdminMenuAction.REVENUE
    )

    with pytest.raises(ValueError):
        handle_admin_callback(111, settings, "admin:delete_all")

    with pytest.raises(ValueError):
        handle_admin_callback(111, settings, "client:revenue")

    with pytest.raises(ValueError):
        handle_admin_callback(111, settings, None)


def test_admin_menu_actions() -> None:
    settings = _settings()
    expected_actions = (
        AdminMenuAction.TODAY,
        AdminMenuAction.THIS_WEEK,
        AdminMenuAction.MANUAL_BOOKING,
        AdminMenuAction.CHANGE_BOOKING,
        AdminMenuAction.CANCEL_BOOKING,
        AdminMenuAction.REVENUE,
        AdminMenuAction.CLIENTS,
        AdminMenuAction.REFERRAL_BONUSES,
    )

    assert admin_menu_actions() == expected_actions

    response = build_admin_menu_response(111, settings)
    assert tuple(button.action for button in response.buttons) == expected_actions
    assert tuple(button.label for button in response.buttons) == (
        "Сегодня",
        "Ближайшие даты",
        "Создать запись",
        "Перенести запись",
        "Отменить запись",
        "Выручка",
        "Клиенты",
        "Бонусы",
    )
    assert tuple(button.callback_data for button in response.buttons) == tuple(
        admin_callback_data(action) for action in expected_actions
    )


def test_admin_user_can_use_client_start_menu() -> None:
    settings = _settings()

    admin_response = handle_admin_menu_command(111, settings)
    client_response = handle_start_command(settings)

    assert admin_response.text == ADMIN_MENU_TEXT
    assert client_response.text == CLIENT_WELCOME_TEXT
    assert client_response.buttons


def test_admin_router_can_be_built_without_registering_clients() -> None:
    router = build_admin_router(_settings())

    assert router.name == "admin"


def _settings() -> Settings:
    return Settings(
        bot_token="test-token",
        admin_telegram_ids=(111, 222),
        database_url="sqlite+aiosqlite:///:memory:",
        timezone="Asia/Tbilisi",
        default_place="Test studio",
        stylist_contact_url="https://t.me/test_stylist",
        env="test",
    )
