from datetime import UTC, datetime, timedelta
from decimal import Decimal

import pytest
from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session

from app.bot.handlers.client import (
    ADMIN_BOOKING_CANCELLED_NOTIFICATION_KIND,
    ADMIN_BOOKING_RESCHEDULED_NOTIFICATION_KIND,
    ADMIN_NEW_BOOKING_NOTIFICATION_KIND,
    CLIENT_WELCOME_TEXT,
    HAIRCUT_CONFIRM_TEXT,
    HAIRCUT_DATE_LIST_TEXT,
    HAIRCUT_SERVICE_CHOICE_TEXT,
    SLOT_UNAVAILABLE_TEXT,
    dispatch_client_callback_async,
    handle_about_master_request,
    handle_active_booking_view,
    handle_client_callback_payload,
    handle_complex_service_redirect,
    handle_consultation_redirect,
    handle_haircut_booking_confirmation,
    handle_haircut_booking_start,
    handle_haircut_date_selection,
    handle_haircut_slot_selection,
    handle_referral_program_request,
    handle_start_command,
    handle_unknown_input,
    notify_admins_about_booking_event,
)
from app.bot.keyboards import (
    ClientMenuAction,
    client_callback_data,
    client_menu_actions,
)
from app.config import Settings
from app.db import session as db_session
from app.db.models import (
    Base,
    Booking,
    BookingStatus,
    Client,
    DeliveryStatus,
    NotificationLog,
    Slot,
    User,
)
from app.services.booking import (
    DEFAULT_HAIRCUT_PRICE,
    HAIRCUT_FEMALE_SERVICE,
    HAIRCUT_MALE_SERVICE,
)


def test_start_menu() -> None:
    response = handle_start_command(_settings())

    assert response.text == CLIENT_WELCOME_TEXT
    assert "Привет" in response.text
    assert "Здесь можно записаться" in response.text
    assert "бонус за 3 новых клиентов" in response.text
    assert "Артём" not in response.text
    assert "SHISHKI" not in response.text
    assert "60 мин" not in response.text
    assert "90 GEL" not in response.text
    assert "Что хотите сделать?" in response.text
    assert tuple(button.action for button in response.buttons) == client_menu_actions()
    assert tuple(button.action for button in response.buttons) == (
        ClientMenuAction.BOOK_HAIRCUT,
        ClientMenuAction.COMPLEX_SERVICE,
        ClientMenuAction.CONSULTATION,
        ClientMenuAction.MY_BOOKING,
        ClientMenuAction.REFERRAL_PROGRAM,
        ClientMenuAction.ABOUT_MASTER,
    )
    assert tuple(button.label for button in response.buttons) == (
        "Стрижка",
        "Окрашивание",
        "Консультация",
        "Моя запись",
        "Рекомендации",
        "О мастере",
    )
    assert handle_unknown_input(_settings()) == response


def test_about_master_response() -> None:
    response = handle_about_master_request()

    assert "Я Артём" in response.text
    assert "Колорист года" in response.text
    assert tuple(button.action for button in response.buttons) == (
        ClientMenuAction.BOOK_HAIRCUT,
        ClientMenuAction.COMPLEX_SERVICE,
        ClientMenuAction.CONSULTATION,
        ClientMenuAction.MY_BOOKING,
        ClientMenuAction.MENU,
    )


def test_referral_program_response_creates_personal_link() -> None:
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)

    with Session(engine, expire_on_commit=False) as session:
        response = handle_referral_program_request(
            session,
            _settings(),
            telegram_user_id=555,
            display_name="Test Client",
            username="test_client",
            bot_username="test_bot",
        )
        session.commit()

        saved_user = session.scalar(select(User).where(User.telegram_id == 555))

    assert saved_user is not None
    assert saved_user.client is not None
    assert "https://t.me/test_bot?start=ref_" in response.text
    assert "классную профессиональную косметику для волос" in response.text
    assert "Засчитано: 0 из 3" in response.text
    assert tuple(button.action for button in response.buttons) == (
        ClientMenuAction.MY_BOOKING,
        ClientMenuAction.BOOK_HAIRCUT,
        ClientMenuAction.MENU,
    )


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

        selected_date = available.starts_at.astimezone(_settings().timezone_info).date()

        choice_response = handle_haircut_booking_start(session, _settings(), now=now)
        assert choice_response.text == HAIRCUT_SERVICE_CHOICE_TEXT
        assert tuple(button.label for button in choice_response.buttons[:2]) == (
            "Мужская стрижка - 100 GEL",
            "Женская стрижка - 120 GEL",
        )

        date_response = handle_haircut_booking_start(
            session,
            _settings(),
            service=HAIRCUT_MALE_SERVICE,
            now=now,
        )
        assert date_response.text == HAIRCUT_DATE_LIST_TEXT
        assert tuple(button.action for button in date_response.buttons) == (
            ClientMenuAction.SELECT_HAIRCUT_DATE,
            ClientMenuAction.MY_BOOKING,
            ClientMenuAction.MENU,
        )
        assert date_response.buttons[0].callback_data == client_callback_data(
            ClientMenuAction.SELECT_HAIRCUT_DATE,
            f"{HAIRCUT_MALE_SERVICE}|{selected_date.isoformat()}",
        )

        slot_response = handle_haircut_date_selection(
            session,
            _settings(),
            selected_date=selected_date,
            service=HAIRCUT_MALE_SERVICE,
            now=now,
        )
        assert tuple(slot.slot_id for slot in slot_response.slots) == (available.id,)
        assert slot_response.slots[0].label == available.starts_at.astimezone(
            _settings().timezone_info
        ).strftime("%H:%M")
        assert tuple(button.action for button in slot_response.buttons) == (
            ClientMenuAction.BOOK_HAIRCUT,
            ClientMenuAction.MY_BOOKING,
            ClientMenuAction.MENU,
        )
        assert blocked.id not in {slot.slot_id for slot in slot_response.slots}
        assert past.id not in {slot.slot_id for slot in slot_response.slots}
        assert slot_response.slots[0].callback_data == client_callback_data(
            ClientMenuAction.SELECT_HAIRCUT_SLOT,
            f"{HAIRCUT_MALE_SERVICE}|{available.id}",
        )

        selection = handle_haircut_slot_selection(
            session,
            _settings(),
            slot_id=available.id,
            service=HAIRCUT_MALE_SERVICE,
            now=now,
        )
        assert "Подтвердить запись?" in selection.text
        assert session.scalar(select(Booking)) is None

        confirmation = handle_haircut_booking_confirmation(
            session,
            _settings(),
            telegram_user_id=555,
            slot_id=available.id,
            service=HAIRCUT_MALE_SERVICE,
            display_name="Test Client",
            username="test_client",
        )
        session.commit()

        booking = confirmation.booking
        saved_user = session.scalar(select(User).where(User.telegram_id == 555))

    assert booking.status is BookingStatus.CONFIRMED
    assert booking.service == HAIRCUT_MALE_SERVICE
    assert booking.slot_id == available.id
    assert booking.price_amount == DEFAULT_HAIRCUT_PRICE
    assert saved_user is not None
    assert saved_user.client is not None
    assert "Запись подтверждена" in confirmation.text
    assert "Мужская стрижка" in confirmation.text
    assert "100 GEL" in confirmation.text


def test_client_callback_requires_confirmation_before_booking() -> None:
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    now = datetime.now(UTC)

    with Session(engine, expire_on_commit=False) as session:
        slot = _create_slot(session, starts_at=now + timedelta(days=1))

        service_choice = handle_client_callback_payload(
            session,
            _settings(),
            callback_payload=client_callback_data(ClientMenuAction.BOOK_HAIRCUT),
            telegram_user_id=555,
            now=now,
        )
        assert service_choice.text == HAIRCUT_SERVICE_CHOICE_TEXT
        assert tuple(button.action for button in service_choice.buttons) == (
            ClientMenuAction.BOOK_HAIRCUT,
            ClientMenuAction.BOOK_HAIRCUT,
            ClientMenuAction.MY_BOOKING,
            ClientMenuAction.MENU,
        )
        assert session.scalar(select(Booking)) is None

        date_list = handle_client_callback_payload(
            session,
            _settings(),
            callback_payload=service_choice.buttons[0].callback_data,
            telegram_user_id=555,
            now=now,
        )
        assert tuple(button.action for button in date_list.buttons) == (
            ClientMenuAction.SELECT_HAIRCUT_DATE,
            ClientMenuAction.MY_BOOKING,
            ClientMenuAction.MENU,
        )
        assert date_list.text == HAIRCUT_DATE_LIST_TEXT
        assert session.scalar(select(Booking)) is None

        slot_list = handle_client_callback_payload(
            session,
            _settings(),
            callback_payload=date_list.buttons[0].callback_data,
            telegram_user_id=555,
            now=now,
        )
        assert tuple(option.slot_id for option in slot_list.slots) == (slot.id,)
        assert tuple(button.action for button in slot_list.buttons) == (
            ClientMenuAction.BOOK_HAIRCUT,
            ClientMenuAction.MY_BOOKING,
            ClientMenuAction.MENU,
        )
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
            ClientMenuAction.SELECT_HAIRCUT_DATE,
            ClientMenuAction.MENU,
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
        assert tuple(button.action for button in booked.buttons) == (
            ClientMenuAction.MY_BOOKING,
            ClientMenuAction.REFERRAL_PROGRAM,
            ClientMenuAction.BOOK_HAIRCUT,
            ClientMenuAction.MENU,
        )
        assert booked.buttons[2].label == "Еще одна стрижка"
        session.commit()

        booking = session.scalar(select(Booking))

    assert booking is not None
    assert booking.status is BookingStatus.CONFIRMED


def test_client_callback_books_female_haircut_with_female_price() -> None:
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    now = datetime.now(UTC)

    with Session(engine, expire_on_commit=False) as session:
        slot = _create_slot(session, starts_at=now + timedelta(days=1))

        date_list = handle_client_callback_payload(
            session,
            _settings(),
            callback_payload=client_callback_data(
                ClientMenuAction.BOOK_HAIRCUT,
                HAIRCUT_FEMALE_SERVICE,
            ),
            telegram_user_id=555,
            now=now,
        )
        assert date_list.text == HAIRCUT_DATE_LIST_TEXT

        slot_list = handle_client_callback_payload(
            session,
            _settings(),
            callback_payload=date_list.buttons[0].callback_data,
            telegram_user_id=555,
            now=now,
        )
        prompt = handle_client_callback_payload(
            session,
            _settings(),
            callback_payload=slot_list.slots[0].callback_data,
            telegram_user_id=555,
            now=now,
        )
        assert "Женская стрижка" in prompt.text
        assert "120 GEL" in prompt.text

        booked = handle_client_callback_payload(
            session,
            _settings(),
            callback_payload=prompt.buttons[0].callback_data,
            telegram_user_id=555,
            display_name="Female Client",
            username="female_client",
            now=now,
        )
        assert booked.should_commit
        session.commit()

        booking = session.scalar(select(Booking))

    assert booking is not None
    assert booking.service == HAIRCUT_FEMALE_SERVICE
    assert booking.price_amount == Decimal("120.00")
    assert booking.slot_id == slot.id


def test_client_cannot_book_more_than_two_haircuts_same_day() -> None:
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    settings = _settings()
    now = datetime(2026, 6, 24, 8, 0, tzinfo=UTC)

    with Session(engine, expire_on_commit=False) as session:
        user = User(telegram_id=555, display_name="Test Client")
        client = Client(user=user, display_name="Test Client")
        first_slot = _create_slot(session, starts_at=now + timedelta(days=1, hours=1))
        second_slot = _create_slot(session, starts_at=now + timedelta(days=1, hours=2))
        third_slot = _create_slot(session, starts_at=now + timedelta(days=1, hours=3))
        session.add(_booking(client, first_slot, first_slot.starts_at))
        session.add(_booking(client, second_slot, second_slot.starts_at))
        session.commit()

        response = handle_client_callback_payload(
            session,
            settings,
            callback_payload=client_callback_data(
                ClientMenuAction.CONFIRM_HAIRCUT,
                third_slot.id,
            ),
            telegram_user_id=555,
            now=now,
        )
        session.rollback()

        bookings = session.scalars(select(Booking)).all()

    assert "максимум 2 активные записи" in response.text
    assert not response.should_commit
    assert tuple(button.action for button in response.buttons) == (
        ClientMenuAction.BOOK_HAIRCUT,
        ClientMenuAction.CONTACT,
        ClientMenuAction.MENU,
    )
    assert len(bookings) == 2


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

    service_response = await dispatch_client_callback_async(
        session_factory,
        _settings(),
        callback_payload=client_callback_data(ClientMenuAction.BOOK_HAIRCUT),
        telegram_user_id=555,
        now=now,
    )
    assert len(service_response.buttons) == 4

    date_response = await dispatch_client_callback_async(
        session_factory,
        _settings(),
        callback_payload=service_response.buttons[0].callback_data,
        telegram_user_id=555,
        now=now,
    )
    assert len(date_response.buttons) == 3

    async with session_factory() as async_session:
        booking_count = await async_session.run_sync(
            lambda session: len(session.scalars(select(Booking)).all())
        )
    assert booking_count == 0

    slot_response = await dispatch_client_callback_async(
        session_factory,
        _settings(),
        callback_payload=date_response.buttons[0].callback_data,
        telegram_user_id=555,
        now=now,
    )
    assert len(slot_response.slots) == 1

    prompt_response = await dispatch_client_callback_async(
        session_factory,
        _settings(),
        callback_payload=slot_response.slots[0].callback_data,
        telegram_user_id=555,
        now=now,
    )
    assert not prompt_response.should_commit
    assert len(prompt_response.buttons) == 3

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
    assert booked_response.admin_notification_booking_id is not None
    assert (
        booked_response.admin_notification_kind == ADMIN_NEW_BOOKING_NOTIFICATION_KIND
    )
    assert len(booked_response.buttons) == 4

    async with session_factory() as async_session:
        booking = await async_session.run_sync(
            lambda session: session.scalar(select(Booking))
        )

    assert booking is not None
    assert booking.status is BookingStatus.CONFIRMED

    await db_session.drop_all(engine)
    await engine.dispose()


@pytest.mark.asyncio
async def test_admins_are_notified_after_client_self_booking() -> None:
    engine = db_session.create_database_engine("sqlite+aiosqlite:///:memory:")
    await db_session.create_all(engine)
    session_factory = db_session.create_session_factory(engine)
    now = datetime.now(UTC)
    settings = _settings()

    async with session_factory() as async_session:
        await async_session.run_sync(
            lambda session: _create_slot(
                session,
                starts_at=now + timedelta(days=1),
            )
        )
        await async_session.commit()

    service_response = await dispatch_client_callback_async(
        session_factory,
        settings,
        callback_payload=client_callback_data(ClientMenuAction.BOOK_HAIRCUT),
        telegram_user_id=555,
        now=now,
    )
    date_response = await dispatch_client_callback_async(
        session_factory,
        settings,
        callback_payload=service_response.buttons[0].callback_data,
        telegram_user_id=555,
        now=now,
    )
    slot_response = await dispatch_client_callback_async(
        session_factory,
        settings,
        callback_payload=date_response.buttons[0].callback_data,
        telegram_user_id=555,
        now=now,
    )
    prompt_response = await dispatch_client_callback_async(
        session_factory,
        settings,
        callback_payload=slot_response.slots[0].callback_data,
        telegram_user_id=555,
        now=now,
    )
    booked_response = await dispatch_client_callback_async(
        session_factory,
        settings,
        callback_payload=prompt_response.buttons[0].callback_data,
        telegram_user_id=555,
        display_name="Notify Client",
        username="notify_client",
        now=now,
    )

    bot = FakeAsyncBot()
    await notify_admins_about_booking_event(
        session_factory,
        settings,
        bot=bot,
        booking_id=booked_response.admin_notification_booking_id,
        kind=booked_response.admin_notification_kind,
    )

    async with session_factory() as async_session:
        logs = await async_session.run_sync(
            lambda session: tuple(
                session.scalars(select(NotificationLog).order_by(NotificationLog.id))
            )
        )

    assert [message[0] for message in bot.messages] == [111]
    assert "Новая запись" in bot.messages[0][1]
    assert "Мужская стрижка" in bot.messages[0][1]
    assert "Notify Client" in bot.messages[0][1]
    assert "ID клиента:" in bot.messages[0][1]
    assert "https://t.me/notify_client" in bot.messages[0][1]
    assert len(logs) == 1
    assert logs[0].kind == ADMIN_NEW_BOOKING_NOTIFICATION_KIND
    assert logs[0].recipient_telegram_id == 111
    assert logs[0].status is DeliveryStatus.SENT

    await db_session.drop_all(engine)
    await engine.dispose()


@pytest.mark.asyncio
async def test_admin_booking_event_notifications_cover_change_and_cancel() -> None:
    engine = db_session.create_database_engine("sqlite+aiosqlite:///:memory:")
    await db_session.create_all(engine)
    session_factory = db_session.create_session_factory(engine)
    now = datetime.now(UTC)
    settings = _settings()

    async with session_factory() as async_session:
        booking_id = await async_session.run_sync(
            lambda session: _persist_booking_for_notification(session, now=now)
        )
        await async_session.commit()

    bot = FakeAsyncBot()
    for kind in (
        ADMIN_NEW_BOOKING_NOTIFICATION_KIND,
        ADMIN_BOOKING_RESCHEDULED_NOTIFICATION_KIND,
        ADMIN_BOOKING_CANCELLED_NOTIFICATION_KIND,
    ):
        await notify_admins_about_booking_event(
            session_factory,
            settings,
            bot=bot,
            booking_id=booking_id,
            kind=kind,
        )

    async with session_factory() as async_session:
        logs = await async_session.run_sync(
            lambda session: tuple(
                session.scalars(select(NotificationLog).order_by(NotificationLog.id))
            )
        )

    assert [message[0] for message in bot.messages] == [111, 111, 111]
    assert "Новая запись" in bot.messages[0][1]
    assert "Клиент перенес запись" in bot.messages[1][1]
    assert "Клиент отменил запись" in bot.messages[2][1]
    assert tuple(log.kind for log in logs) == (
        ADMIN_NEW_BOOKING_NOTIFICATION_KIND,
        ADMIN_BOOKING_RESCHEDULED_NOTIFICATION_KIND,
        ADMIN_BOOKING_CANCELLED_NOTIFICATION_KIND,
    )
    assert all(log.status is DeliveryStatus.SENT for log in logs)

    await db_session.drop_all(engine)
    await engine.dispose()


def test_client_can_view_and_cancel_active_booking() -> None:
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    now = datetime.now(UTC)

    with Session(engine, expire_on_commit=False) as session:
        user = User(telegram_id=555, display_name="Test Client")
        client = Client(user=user, display_name="Test Client")
        slot = _create_slot(session, starts_at=now + timedelta(days=1))
        session.add(_booking(client, slot, now + timedelta(days=1)))
        session.commit()

        my_booking = handle_client_callback_payload(
            session,
            _settings(),
            callback_payload=client_callback_data(ClientMenuAction.MY_BOOKING),
            telegram_user_id=555,
            now=now,
        )
        assert "Ваша запись:" in my_booking.text
        assert "Что хотите сделать?" in my_booking.text
        assert "Если нужно изменить запись" not in my_booking.text
        assert tuple(button.action for button in my_booking.buttons) == (
            ClientMenuAction.CHANGE_BOOKING,
            ClientMenuAction.CANCEL_BOOKING,
            ClientMenuAction.REFERRAL_PROGRAM,
            ClientMenuAction.BOOK_HAIRCUT,
            ClientMenuAction.MENU,
        )
        assert my_booking.buttons[-2].label == "Еще одна стрижка"

        cancel_prompt = handle_client_callback_payload(
            session,
            _settings(),
            callback_payload=client_callback_data(ClientMenuAction.CANCEL_BOOKING),
            telegram_user_id=555,
            now=now,
        )
        assert "Точно отменить эту запись?" in cancel_prompt.text
        assert tuple(button.action for button in cancel_prompt.buttons) == (
            ClientMenuAction.CONFIRM_CANCEL,
            ClientMenuAction.MY_BOOKING,
        )

        cancelled = handle_client_callback_payload(
            session,
            _settings(),
            callback_payload=client_callback_data(ClientMenuAction.CONFIRM_CANCEL),
            telegram_user_id=555,
            now=now,
        )
        assert cancelled.should_commit
        assert (
            cancelled.admin_notification_kind
            == ADMIN_BOOKING_CANCELLED_NOTIFICATION_KIND
        )
        assert cancelled.admin_notification_booking_id is not None
        session.commit()

        booking = session.scalar(select(Booking))

    assert booking is not None
    assert booking.status is BookingStatus.CANCELLED_BY_CLIENT
    assert booking.status_history[-1].actor == "client"


def test_client_can_reschedule_active_booking_to_new_slot() -> None:
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    now = datetime.now(UTC)

    with Session(engine, expire_on_commit=False) as session:
        user = User(telegram_id=555, display_name="Test Client")
        client = Client(user=user, display_name="Test Client")
        old_slot = _create_slot(session, starts_at=now + timedelta(days=1))
        new_slot = _create_slot(session, starts_at=now + timedelta(days=2))
        session.add(_booking(client, old_slot, now + timedelta(days=1)))
        session.commit()

        date_list = handle_client_callback_payload(
            session,
            _settings(),
            callback_payload=client_callback_data(ClientMenuAction.CHANGE_BOOKING),
            telegram_user_id=555,
            now=now,
        )
        assert tuple(button.action for button in date_list.buttons) == (
            ClientMenuAction.SELECT_RESCHEDULE_DATE,
            ClientMenuAction.MY_BOOKING,
            ClientMenuAction.MENU,
        )

        slot_list = handle_client_callback_payload(
            session,
            _settings(),
            callback_payload=date_list.buttons[0].callback_data,
            telegram_user_id=555,
            now=now,
        )
        assert tuple(slot.slot_id for slot in slot_list.slots) == (new_slot.id,)
        assert slot_list.slots[0].callback_data == client_callback_data(
            ClientMenuAction.SELECT_RESCHEDULE_SLOT,
            new_slot.id,
        )

        prompt = handle_client_callback_payload(
            session,
            _settings(),
            callback_payload=slot_list.slots[0].callback_data,
            telegram_user_id=555,
            now=now,
        )
        assert "Подтвердить новое время?" in prompt.text
        assert tuple(button.action for button in prompt.buttons) == (
            ClientMenuAction.CONFIRM_RESCHEDULE,
            ClientMenuAction.SELECT_RESCHEDULE_DATE,
            ClientMenuAction.MENU,
        )

        rescheduled = handle_client_callback_payload(
            session,
            _settings(),
            callback_payload=prompt.buttons[0].callback_data,
            telegram_user_id=555,
            now=now,
        )
        assert rescheduled.should_commit
        assert (
            rescheduled.admin_notification_kind
            == ADMIN_BOOKING_RESCHEDULED_NOTIFICATION_KIND
        )
        assert rescheduled.admin_notification_booking_id is not None
        session.commit()

        booking = session.scalar(select(Booking))

    assert booking is not None
    assert booking.status is BookingStatus.RESCHEDULED
    assert booking.slot_id == new_slot.id
    assert booking.status_history[-1].actor == "client"


def test_stale_slot_callback_is_recoverable() -> None:
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    now = datetime.now(UTC)

    with Session(engine) as session:
        stale_slot = _create_slot(session, starts_at=now - timedelta(days=1))
        available_slot = _create_slot(session, starts_at=now + timedelta(days=1))

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

    assert response.text.startswith(SLOT_UNAVAILABLE_TEXT)
    assert HAIRCUT_DATE_LIST_TEXT in response.text
    assert tuple(button.action for button in response.buttons) == (
        ClientMenuAction.SELECT_HAIRCUT_DATE,
        ClientMenuAction.MY_BOOKING,
        ClientMenuAction.MENU,
    )
    assert response.buttons[0].callback_data == client_callback_data(
        ClientMenuAction.SELECT_HAIRCUT_DATE,
        (
            f"{HAIRCUT_MALE_SERVICE}|"
            f"{available_slot.starts_at.astimezone(_settings().timezone_info).date().isoformat()}"
        ),
    )


def test_confirming_taken_slot_returns_fresh_dates_without_duplicate_booking() -> None:
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    now = datetime.now(UTC)

    with Session(engine, expire_on_commit=False) as session:
        first_client = Client(
            user=User(telegram_id=111, display_name="First Client"),
            display_name="First Client",
        )
        taken_slot = _create_slot(session, starts_at=now + timedelta(days=1))
        next_slot = _create_slot(session, starts_at=now + timedelta(days=2))
        next_slot_date = (
            next_slot.starts_at.astimezone(_settings().timezone_info).date().isoformat()
        )
        session.add(_booking(first_client, taken_slot, taken_slot.starts_at))
        session.commit()

        response = handle_client_callback_payload(
            session,
            _settings(),
            callback_payload=client_callback_data(
                ClientMenuAction.CONFIRM_HAIRCUT,
                taken_slot.id,
            ),
            telegram_user_id=222,
            display_name="Second Client",
            now=now,
        )
        session.rollback()

        bookings = session.scalars(select(Booking)).all()
        users = session.scalars(select(User)).all()

    assert response.text.startswith(SLOT_UNAVAILABLE_TEXT)
    assert HAIRCUT_DATE_LIST_TEXT in response.text
    assert not response.should_commit
    assert tuple(button.action for button in response.buttons) == (
        ClientMenuAction.SELECT_HAIRCUT_DATE,
        ClientMenuAction.MY_BOOKING,
        ClientMenuAction.MENU,
    )
    assert response.buttons[0].callback_data == client_callback_data(
        ClientMenuAction.SELECT_HAIRCUT_DATE,
        f"{HAIRCUT_MALE_SERVICE}|{next_slot_date}",
    )
    assert len(bookings) == 1
    assert {user.telegram_id for user in users} == {111}


def test_active_booking_view_ignores_past_bookings() -> None:
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    now = datetime.now(UTC)

    with Session(engine) as session:
        user = User(telegram_id=555, display_name="Test Client")
        client = Client(user=user, display_name="Test Client")
        past_starts_at = now - timedelta(days=1)
        future_starts_at = now + timedelta(days=1, hours=2)
        past_slot = _create_slot(session, starts_at=past_starts_at)
        future_slot = _create_slot(session, starts_at=future_starts_at)
        session.add_all(
            [
                _booking(client, past_slot, past_starts_at),
                _booking(client, future_slot, future_starts_at),
            ]
        )
        session.commit()

        response = handle_active_booking_view(
            session,
            _settings(),
            telegram_user_id=555,
            now=now,
        )

    assert "Ваша запись:" in response.text
    assert future_starts_at.strftime("%H:%M") in response.text
    assert past_starts_at.strftime("%H:%M") not in response.text


def test_no_active_booking_view_offers_service_choices() -> None:
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)

    with Session(engine) as session:
        response = handle_client_callback_payload(
            session,
            _settings(),
            callback_payload=client_callback_data(ClientMenuAction.MY_BOOKING),
            telegram_user_id=555,
        )

    assert "У вас пока нет активной записи" in response.text
    assert tuple(button.action for button in response.buttons) == (
        ClientMenuAction.BOOK_HAIRCUT,
        ClientMenuAction.COMPLEX_SERVICE,
        ClientMenuAction.CONSULTATION,
        ClientMenuAction.MENU,
    )


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
            display_name="Color Client",
            username="color_client",
        )
        assert callback_response.should_commit
        session.commit()
        after = session.scalars(select(Booking)).all()
        saved_user = session.scalar(select(User).where(User.telegram_id == 555))
        saved_client = session.scalar(
            select(Client).join(User).where(User.telegram_id == 555)
        )

    assert before == []
    assert after == []
    assert saved_user is not None
    assert saved_client is not None
    assert "Окрашивание требует консультации" in response.text
    assert "Окрашивание требует консультации" in callback_response.text
    assert "https://t.me/test_stylist" in response.text
    assert "сам внесу запись" in response.text
    assert tuple(button.action for button in callback_response.buttons) == (
        ClientMenuAction.BOOK_HAIRCUT,
        ClientMenuAction.CONSULTATION,
        ClientMenuAction.MENU,
    )


def test_consultation_redirect() -> None:
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)

    with Session(engine) as session:
        response = handle_consultation_redirect(_settings())
        callback_response = handle_client_callback_payload(
            session,
            _settings(),
            callback_payload=client_callback_data(ClientMenuAction.CONSULTATION),
            telegram_user_id=555,
            display_name="Consult Client",
            username="consult_client",
        )
        assert callback_response.should_commit
        session.commit()
        bookings = session.scalars(select(Booking)).all()
        saved_user = session.scalar(select(User).where(User.telegram_id == 555))
        saved_client = session.scalar(
            select(Client).join(User).where(User.telegram_id == 555)
        )

    assert bookings == []
    assert saved_user is not None
    assert saved_client is not None
    assert "Для консультации" in response.text
    assert "Для консультации" in callback_response.text
    assert "https://t.me/test_stylist" in callback_response.text
    assert tuple(button.action for button in callback_response.buttons) == (
        ClientMenuAction.BOOK_HAIRCUT,
        ClientMenuAction.COMPLEX_SERVICE,
        ClientMenuAction.MENU,
    )


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


def _persist_booking_for_notification(session: Session, *, now: datetime) -> int:
    user = User(telegram_id=555, display_name="Notify Client")
    client = Client(user=user, display_name="Notify Client")
    slot = _create_slot(session, starts_at=now + timedelta(days=1))
    booking = _booking(client, slot, slot.starts_at)
    session.add(booking)
    session.flush()
    return booking.id


class FakeAsyncBot:
    def __init__(self) -> None:
        self.messages: list[tuple[int, str]] = []

    async def send_message(self, recipient_telegram_id: int, text: str) -> None:
        self.messages.append((recipient_telegram_id, text))
