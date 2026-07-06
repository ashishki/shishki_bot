from datetime import UTC, datetime, timedelta
from decimal import Decimal

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from app.bot.handlers.admin import (
    AdminAccessDenied,
    handle_admin_booking_detail_view,
    handle_admin_cancel_confirm_prompt,
    handle_admin_client_card,
    handle_admin_client_card_view,
    handle_admin_clients_list,
    handle_admin_reschedule_confirm_prompt,
    handle_admin_schedule_date_view,
    handle_admin_schedule_dates,
)
from app.bot.keyboards import AdminMenuAction, admin_callback_data
from app.config import Settings
from app.db.models import Base, Booking, BookingStatus, Client, Slot, User
from app.services.clients import ClientServiceError, client_card_summary


def test_client_card_summary() -> None:
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)

    with Session(engine, expire_on_commit=False) as session:
        client = _create_client(
            session,
            display_name="Test Client",
            username="test_client",
            notes="Prefers mornings",
        )
        first_visit = _create_booking(
            session,
            client=client,
            starts_at=datetime(2026, 6, 20, 10, 0, tzinfo=UTC),
            service="haircut",
            final_amount=Decimal("90.00"),
            status=BookingStatus.COMPLETED,
        )
        second_visit = _create_booking(
            session,
            client=client,
            starts_at=datetime(2026, 6, 23, 11, 0, tzinfo=UTC),
            service="coloring",
            final_amount=Decimal("250.00"),
            status=BookingStatus.COMPLETED,
        )
        _create_booking(
            session,
            client=client,
            starts_at=datetime(2026, 6, 24, 11, 0, tzinfo=UTC),
            service="haircut",
            final_amount=Decimal("999.00"),
            status=BookingStatus.CANCELLED_BY_CLIENT,
        )
        session.commit()

        card = client_card_summary(session, client_id=client.id)

    assert card.client_id == client.id
    assert card.display_name == "Test Client"
    assert card.username == "test_client"
    assert card.notes == "Prefers mornings"
    assert card.visit_count == 2
    assert card.total_spent == Decimal("340.00")
    assert card.last_visit == datetime(2026, 6, 23, 11, 0, tzinfo=UTC)
    assert card.services_summary == {"haircut": 1, "coloring": 1}
    assert tuple(visit.booking_id for visit in card.visits) == (
        first_visit.id,
        second_visit.id,
    )


def test_client_total_spent() -> None:
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)

    with Session(engine, expire_on_commit=False) as session:
        client = _create_client(session, display_name=None, username="history_client")
        _create_booking(
            session,
            client=client,
            starts_at=datetime(2026, 6, 20, 10, 0, tzinfo=UTC),
            service="haircut",
            final_amount=Decimal("90.00"),
            status=BookingStatus.COMPLETED,
        )
        _create_booking(
            session,
            client=client,
            starts_at=datetime(2026, 6, 21, 10, 0, tzinfo=UTC),
            service="manual complex service",
            final_amount=Decimal("180.00"),
            status=BookingStatus.COMPLETED,
        )
        _create_booking(
            session,
            client=client,
            starts_at=datetime(2026, 6, 22, 10, 0, tzinfo=UTC),
            service="confirmed only",
            final_amount=Decimal("300.00"),
            status=BookingStatus.CONFIRMED,
        )
        _create_booking(
            session,
            client=client,
            starts_at=datetime(2026, 6, 23, 10, 0, tzinfo=UTC),
            service="no show",
            final_amount=Decimal("400.00"),
            status=BookingStatus.NO_SHOW,
        )
        _create_booking(
            session,
            client=client,
            starts_at=datetime(2026, 6, 24, 10, 0, tzinfo=UTC),
            service="missing final amount",
            final_amount=None,
            status=BookingStatus.COMPLETED,
        )

        other_client = _create_client(
            session,
            telegram_id=456,
            username="other_client",
        )
        _create_booking(
            session,
            client=other_client,
            starts_at=datetime(2026, 6, 25, 10, 0, tzinfo=UTC),
            service="haircut",
            final_amount=Decimal("999.00"),
            status=BookingStatus.COMPLETED,
        )
        session.commit()

        card = client_card_summary(session, client_id=client.id)

    assert card.display_name == "@history_client"
    assert card.visit_count == 2
    assert card.total_spent == Decimal("270.00")
    assert card.services_summary == {"haircut": 1, "manual complex service": 1}


def test_admin_client_card_requires_allowlist() -> None:
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    settings = _settings()

    with Session(engine, expire_on_commit=False) as session:
        client = _create_client(session)
        _create_booking(
            session,
            client=client,
            starts_at=datetime(2026, 6, 20, 10, 0, tzinfo=UTC),
            service="haircut",
            final_amount=Decimal("90.00"),
            status=BookingStatus.COMPLETED,
        )

        with pytest.raises(AdminAccessDenied):
            handle_admin_client_card(
                session,
                settings,
                telegram_user_id=222,
                client_id=client.id,
            )

        response = handle_admin_client_card(
            session,
            settings,
            telegram_user_id=111,
            client_id=client.id,
        )

    assert response.client_card.total_spent == Decimal("90.00")


def test_admin_clients_list_and_card_view_include_contact_current_and_history() -> None:
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    settings = _settings()
    now = datetime(2026, 6, 23, 10, 0, tzinfo=UTC)

    with Session(engine, expire_on_commit=False) as session:
        client = _create_client(
            session,
            display_name="Test Client",
            username="test_client",
            notes="Prefers mornings",
        )
        active = _create_booking(
            session,
            client=client,
            starts_at=now + timedelta(days=1),
            service="haircut",
            final_amount=None,
            status=BookingStatus.CONFIRMED,
        )
        completed = _create_booking(
            session,
            client=client,
            starts_at=now - timedelta(days=2),
            service="coloring",
            final_amount=Decimal("250.00"),
            status=BookingStatus.COMPLETED,
        )
        session.commit()

        clients = handle_admin_clients_list(
            session,
            settings,
            telegram_user_id=111,
        )
        card = handle_admin_client_card_view(
            session,
            settings,
            telegram_user_id=111,
            client_id=client.id,
            now=now,
        )

    assert clients.text == "Клиенты"
    assert clients.buttons[0].callback_data == admin_callback_data(
        AdminMenuAction.CLIENT_CARD,
        client.id,
    )
    assert "Карточка клиента: Test Client" in card.text
    assert "https://t.me/test_client" in card.text
    assert f"#{active.id}" in card.text
    assert "подтверждена" in card.text
    assert f"#{completed.id}" in card.text
    assert "завершена" in card.text
    assert tuple(button.label for button in card.buttons) == (
        "Открыть чат",
        "Создать запись",
        "Назад к клиентам",
        "Главная",
    )
    assert card.buttons[0].url == "https://t.me/test_client"


def test_admin_schedule_dates_date_view_and_booking_actions() -> None:
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    settings = _settings()
    starts_at = datetime(2026, 6, 27, 10, 0, tzinfo=UTC)

    with Session(engine, expire_on_commit=False) as session:
        client = _create_client(session, display_name="Test Client")
        booking = _create_booking(
            session,
            client=client,
            starts_at=starts_at,
            service="haircut",
            final_amount=None,
            status=BookingStatus.CONFIRMED,
        )
        target_slot = Slot(
            starts_at=starts_at + timedelta(hours=1),
            ends_at=starts_at + timedelta(hours=2),
            place="Test studio",
        )
        session.add(target_slot)
        session.commit()

        dates = handle_admin_schedule_dates(
            session,
            settings,
            telegram_user_id=111,
            start_date=starts_at.date(),
            days=7,
        )
        day = handle_admin_schedule_date_view(
            session,
            settings,
            telegram_user_id=111,
            selected_date=starts_at.date(),
        )
        detail = handle_admin_booking_detail_view(
            session,
            settings,
            telegram_user_id=111,
            booking_id=booking.id,
        )
        move_prompt = handle_admin_reschedule_confirm_prompt(
            session,
            settings,
            telegram_user_id=111,
            booking_id=booking.id,
            slot_id=target_slot.id,
        )
        cancel_prompt = handle_admin_cancel_confirm_prompt(
            session,
            settings,
            telegram_user_id=111,
            booking_id=booking.id,
        )

    assert dates.text == "Даты расписания"
    assert dates.buttons[0].label == "Сб, 27 июня"
    assert "Записей: 1" in day.text
    assert f"#{booking.id}" in day.text
    assert "Запись #" in detail.text
    assert tuple(button.label for button in detail.buttons)[:3] == (
        "Открыть чат",
        "Перенести",
        "Отменить",
    )
    assert "Перенести запись" in move_prompt.text
    assert move_prompt.buttons[0].label == "Подтвердить перенос"
    assert "Точно отменить эту запись?" in cancel_prompt.text
    assert cancel_prompt.buttons[0].label == "Подтвердить отмену"


def test_client_card_missing_client() -> None:
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)

    with Session(engine) as session, pytest.raises(ClientServiceError):
        client_card_summary(session, client_id=999)


def _settings() -> Settings:
    return Settings(
        bot_token="test-token",
        admin_telegram_ids=(111,),
        database_url="sqlite+aiosqlite:///:memory:",
        timezone="Asia/Tbilisi",
        default_place="Test studio",
        stylist_contact_url="https://t.me/test_stylist",
        env="test",
    )


def _create_client(
    session: Session,
    *,
    telegram_id: int = 123,
    display_name: str | None = "Test Client",
    username: str | None = "test_client",
    notes: str | None = None,
) -> Client:
    client = Client(
        user=User(
            telegram_id=telegram_id,
            username=username,
            display_name=display_name,
        ),
        display_name=display_name,
        notes=notes,
    )
    session.add(client)
    session.flush()
    return client


def _create_booking(
    session: Session,
    *,
    client: Client,
    starts_at: datetime,
    service: str,
    final_amount: Decimal | None,
    status: BookingStatus,
) -> Booking:
    slot = Slot(
        starts_at=starts_at,
        ends_at=starts_at + timedelta(hours=1),
        place="Test studio",
    )
    booking = Booking(
        client=client,
        slot=slot,
        service=service,
        starts_at=starts_at,
        ends_at=starts_at + timedelta(hours=1),
        duration_minutes=60,
        place="Test studio",
        price_amount=Decimal("90.00"),
        final_amount=final_amount,
        status=status,
    )
    session.add(booking)
    session.flush()
    return booking
