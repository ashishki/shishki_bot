from datetime import UTC, datetime, timedelta
from decimal import Decimal

import pytest
from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session

from app.bot.handlers.client import (
    CLIENT_WELCOME_TEXT,
    HAIRCUT_CONFIRM_TEXT,
    SLOT_UNAVAILABLE_TEXT,
    dispatch_client_callback_async,
    handle_active_booking_view,
    handle_client_callback_payload,
    handle_complex_service_redirect,
    handle_haircut_booking_confirmation,
    handle_haircut_booking_start,
    handle_haircut_slot_selection,
    handle_start_command,
    handle_unknown_input,
)
from app.bot.keyboards import (
    ClientMenuAction,
    client_callback_data,
    client_menu_actions,
)
from app.config import Settings
from app.db import session as db_session
from app.db.models import Base, Booking, BookingStatus, Client, Slot, User
from app.services.booking import DEFAULT_HAIRCUT_PRICE


def test_start_menu() -> None:
    response = handle_start_command(_settings())

    assert response.text == CLIENT_WELCOME_TEXT
    assert "60 minutes" in response.text
    assert "90 GEL" in response.text
    assert "complex services require a personal consultation" in response.text
    assert tuple(button.action for button in response.buttons) == client_menu_actions()
    assert tuple(button.action for button in response.buttons) == (
        ClientMenuAction.BOOK_HAIRCUT,
        ClientMenuAction.COMPLEX_SERVICE,
        ClientMenuAction.MY_BOOKING,
        ClientMenuAction.RESCHEDULE_CANCEL,
        ClientMenuAction.CONTACT,
    )
    assert handle_unknown_input(_settings()) == response


def test_client_haircut_booking_flow() -> None:
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    now = datetime.now(UTC)

    with Session(engine, expire_on_commit=False) as session:
        available = _create_slot(session, starts_at=now + timedelta(days=1))
        blocked = _create_slot(
            session,
            starts_at=now + timedelta(days=2),
            is_blocked=True,
        )
        past = _create_slot(session, starts_at=now - timedelta(days=1))

        slot_response = handle_haircut_booking_start(session, _settings(), now=now)
        assert tuple(slot.slot_id for slot in slot_response.slots) == (available.id,)
        assert blocked.id not in {slot.slot_id for slot in slot_response.slots}
        assert past.id not in {slot.slot_id for slot in slot_response.slots}
        assert slot_response.slots[0].callback_data == client_callback_data(
            ClientMenuAction.SELECT_HAIRCUT_SLOT,
            available.id,
        )

        selection = handle_haircut_slot_selection(
            session,
            _settings(),
            slot_id=available.id,
            now=now,
        )
        assert "Confirm this haircut booking?" in selection.text
        assert session.scalar(select(Booking)) is None

        confirmation = handle_haircut_booking_confirmation(
            session,
            _settings(),
            telegram_user_id=555,
            slot_id=available.id,
            display_name="Test Client",
            username="test_client",
        )
        session.commit()

        booking = confirmation.booking
        saved_user = session.scalar(select(User).where(User.telegram_id == 555))

    assert booking.status is BookingStatus.CONFIRMED
    assert booking.service == "haircut"
    assert booking.slot_id == available.id
    assert booking.price_amount == DEFAULT_HAIRCUT_PRICE
    assert saved_user is not None
    assert saved_user.client is not None
    assert "Booking confirmed" in confirmation.text
    assert "Service: haircut" in confirmation.text
    assert "Price: 90 GEL" in confirmation.text


def test_client_callback_requires_confirmation_before_booking() -> None:
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    now = datetime.now(UTC)

    with Session(engine, expire_on_commit=False) as session:
        slot = _create_slot(session, starts_at=now + timedelta(days=1))

        slot_list = handle_client_callback_payload(
            session,
            _settings(),
            callback_payload=client_callback_data(ClientMenuAction.BOOK_HAIRCUT),
            telegram_user_id=555,
            now=now,
        )
        assert tuple(option.slot_id for option in slot_list.slots) == (slot.id,)
        assert session.scalar(select(Booking)) is None

        confirmation_prompt = handle_client_callback_payload(
            session,
            _settings(),
            callback_payload=slot_list.slots[0].callback_data,
            telegram_user_id=555,
            now=now,
        )
        assert HAIRCUT_CONFIRM_TEXT in confirmation_prompt.text
        assert tuple(button.action for button in confirmation_prompt.buttons) == (
            ClientMenuAction.CONFIRM_HAIRCUT,
        )
        assert session.scalar(select(Booking)) is None

        booked = handle_client_callback_payload(
            session,
            _settings(),
            callback_payload=confirmation_prompt.buttons[0].callback_data,
            telegram_user_id=555,
            display_name="Test Client",
            username="test_client",
            now=now,
        )
        assert booked.should_commit
        session.commit()

        booking = session.scalar(select(Booking))

    assert booking is not None
    assert booking.status is BookingStatus.CONFIRMED


@pytest.mark.asyncio
async def test_async_callback_dispatch_commits_only_confirmation() -> None:
    engine = db_session.create_database_engine("sqlite+aiosqlite:///:memory:")
    await db_session.create_all(engine)
    session_factory = db_session.create_session_factory(engine)
    now = datetime.now(UTC)

    async with session_factory() as async_session:
        await async_session.run_sync(
            lambda session: _create_slot(
                session,
                starts_at=now + timedelta(days=1),
            )
        )
        await async_session.commit()

    list_response = await dispatch_client_callback_async(
        session_factory,
        _settings(),
        callback_payload=client_callback_data(ClientMenuAction.BOOK_HAIRCUT),
        telegram_user_id=555,
        now=now,
    )
    assert len(list_response.slots) == 1

    async with session_factory() as async_session:
        booking_count = await async_session.run_sync(
            lambda session: len(session.scalars(select(Booking)).all())
        )
    assert booking_count == 0

    prompt_response = await dispatch_client_callback_async(
        session_factory,
        _settings(),
        callback_payload=list_response.slots[0].callback_data,
        telegram_user_id=555,
        now=now,
    )
    assert not prompt_response.should_commit
    assert len(prompt_response.buttons) == 1

    booked_response = await dispatch_client_callback_async(
        session_factory,
        _settings(),
        callback_payload=prompt_response.buttons[0].callback_data,
        telegram_user_id=555,
        display_name="Async Client",
        username="async_client",
        now=now,
    )
    assert booked_response.should_commit

    async with session_factory() as async_session:
        booking = await async_session.run_sync(
            lambda session: session.scalar(select(Booking))
        )

    assert booking is not None
    assert booking.status is BookingStatus.CONFIRMED

    await db_session.drop_all(engine)
    await engine.dispose()


def test_stale_slot_callback_is_recoverable() -> None:
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    now = datetime.now(UTC)

    with Session(engine) as session:
        stale_slot = _create_slot(session, starts_at=now - timedelta(days=1))

        response = handle_client_callback_payload(
            session,
            _settings(),
            callback_payload=client_callback_data(
                ClientMenuAction.SELECT_HAIRCUT_SLOT,
                stale_slot.id,
            ),
            telegram_user_id=555,
            now=now,
        )

    assert response.text == SLOT_UNAVAILABLE_TEXT


def test_active_booking_view_ignores_past_bookings() -> None:
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    now = datetime.now(UTC)

    with Session(engine) as session:
        user = User(telegram_id=555, display_name="Test Client")
        client = Client(user=user, display_name="Test Client")
        past_slot = _create_slot(session, starts_at=now - timedelta(days=1))
        future_slot = _create_slot(session, starts_at=now + timedelta(days=1))
        session.add_all(
            [
                _booking(client, past_slot, now - timedelta(days=1)),
                _booking(client, future_slot, now + timedelta(days=1)),
            ]
        )
        session.commit()

        response = handle_active_booking_view(
            session,
            _settings(),
            telegram_user_id=555,
            now=now,
        )

    assert "Your active booking" in response.text
    assert (now + timedelta(days=1)).strftime("%Y-%m-%d") in response.text
    assert (now - timedelta(days=1)).strftime("%Y-%m-%d") not in response.text


def test_complex_service_redirect() -> None:
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)

    with Session(engine) as session:
        before = session.scalars(select(Booking)).all()
        response = handle_complex_service_redirect(_settings())
        callback_response = handle_client_callback_payload(
            session,
            _settings(),
            callback_payload=client_callback_data(ClientMenuAction.COMPLEX_SERVICE),
            telegram_user_id=555,
        )
        after = session.scalars(select(Booking)).all()

    assert before == []
    assert after == []
    assert "personal consultation" in response.text
    assert "personal consultation" in callback_response.text
    assert "https://t.me/test_stylist" in response.text
    assert "manually" in response.text


def _settings() -> Settings:
    return Settings(
        bot_token="test-token",
        admin_telegram_ids=(111,),
        database_url="sqlite+aiosqlite:///:memory:",
        timezone="Asia/Tbilisi",
        default_place="Test studio",
        default_map_url="https://maps.example/test",
        stylist_contact_url="https://t.me/test_stylist",
        env="test",
    )


def _create_slot(
    session: Session,
    *,
    starts_at: datetime,
    is_blocked: bool = False,
) -> Slot:
    slot = Slot(
        starts_at=starts_at,
        ends_at=starts_at + timedelta(hours=1),
        place="Test studio",
        is_blocked=is_blocked,
    )
    session.add(slot)
    session.flush()
    return slot


def _booking(client: Client, slot: Slot, starts_at: datetime) -> Booking:
    return Booking(
        client=client,
        slot=slot,
        service="haircut",
        starts_at=starts_at,
        ends_at=starts_at + timedelta(hours=1),
        duration_minutes=60,
        place="Test studio",
        price_amount=Decimal("90.00"),
        status=BookingStatus.CONFIRMED,
    )
