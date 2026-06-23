from contextlib import contextmanager
from datetime import UTC, datetime, timedelta
from decimal import Decimal

import pytest
from sqlalchemy import create_engine, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.bot.handlers.admin import (
    AdminAccessDenied,
    handle_admin_cancel_booking,
    handle_admin_manual_booking,
    handle_admin_reschedule_booking,
    handle_admin_update_booking_details,
)
from app.config import Settings
from app.db.models import (
    Base,
    BookingStatus,
    Client,
    DeliveryStatus,
    NotificationLog,
    Slot,
    User,
)
from app.services import booking as booking_service
from app.services.booking import BookingServiceError, SlotUnavailableError


def test_admin_manual_booking() -> None:
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    starts_at = datetime.now(UTC) + timedelta(days=1)

    with Session(engine, expire_on_commit=False) as session:
        client = _create_client(session)
        slot = _create_slot(session, starts_at=starts_at)

        response = handle_admin_manual_booking(
            session,
            _settings(),
            telegram_user_id=111,
            client_id=client.id,
            slot_id=slot.id,
            service="coloring",
            duration_minutes=180,
            price_amount=Decimal("250.00"),
            place="Private studio",
            notes="Synthetic test notes",
        )
        session.commit()

        booking = response.booking

        whitespace_slot = _create_slot(session, starts_at=starts_at + timedelta(days=1))
        with pytest.raises(BookingServiceError, match="place is required"):
            handle_admin_manual_booking(
                session,
                _settings(),
                telegram_user_id=111,
                client_id=client.id,
                slot_id=whitespace_slot.id,
                service="hair treatment",
                duration_minutes=60,
                price_amount=Decimal("120.00"),
                place="   ",
            )

    assert booking.status is BookingStatus.CONFIRMED
    assert booking.service == "coloring"
    assert booking.duration_minutes == 180
    assert booking.ends_at == starts_at + timedelta(minutes=180)
    assert booking.price_amount == Decimal("250.00")
    assert booking.place == "Private studio"
    assert booking.notes == "Synthetic test notes"
    assert len(booking.status_history) == 1
    assert booking.status_history[0].actor == "admin"


def test_admin_reschedule_notifies_client() -> None:
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    original_start = datetime.now(UTC) + timedelta(days=1)
    new_start = datetime.now(UTC) + timedelta(days=2)
    sender = FakeSender()

    with Session(engine, expire_on_commit=False) as session:
        client = _create_client(session)
        original_slot = _create_slot(session, starts_at=original_start)
        new_slot = _create_slot(session, starts_at=new_start)
        booking = handle_admin_manual_booking(
            session,
            _settings(),
            telegram_user_id=111,
            client_id=client.id,
            slot_id=original_slot.id,
            service="coloring",
            duration_minutes=120,
            price_amount=Decimal("220.00"),
        ).booking
        session.commit()

        response = handle_admin_reschedule_booking(
            session,
            _settings(),
            sender=sender,
            telegram_user_id=111,
            booking_id=booking.id,
            new_slot_id=new_slot.id,
            reason="client requested later date",
        )
        session.commit()

        saved_log = session.scalar(select(NotificationLog))

    assert response.booking.status is BookingStatus.RESCHEDULED
    assert response.booking.slot_id == new_slot.id
    assert response.booking.starts_at == new_start
    assert len(response.booking.status_history) == 2
    assert response.booking.status_history[-1].old_status is BookingStatus.CONFIRMED
    assert response.booking.status_history[-1].new_status is BookingStatus.RESCHEDULED
    assert response.notification_log is saved_log
    assert saved_log is not None
    assert saved_log.status is DeliveryStatus.SENT
    assert saved_log.kind == "booking_rescheduled"
    assert sender.messages[0][0] == 123
    assert "Booking rescheduled" in sender.messages[0][1]
    assert new_start.strftime("%Y-%m-%d") in sender.messages[0][1]


def test_admin_cancel_notifies_client() -> None:
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    starts_at = datetime.now(UTC) + timedelta(days=1)
    sender = FakeSender()

    with Session(engine, expire_on_commit=False) as session:
        client = _create_client(session)
        slot = _create_slot(session, starts_at=starts_at)
        booking = handle_admin_manual_booking(
            session,
            _settings(),
            telegram_user_id=111,
            client_id=client.id,
            slot_id=slot.id,
            service="coloring",
            duration_minutes=120,
            price_amount=Decimal("220.00"),
        ).booking
        session.commit()

        response = handle_admin_cancel_booking(
            session,
            _settings(),
            sender=sender,
            telegram_user_id=111,
            booking_id=booking.id,
            reason="stylist unavailable",
        )
        session.commit()

        saved_log = session.scalar(select(NotificationLog))
        second_client = _create_client(session, telegram_id=456)
        second_booking = handle_admin_manual_booking(
            session,
            _settings(),
            telegram_user_id=111,
            client_id=second_client.id,
            slot_id=slot.id,
            service="hair treatment",
            duration_minutes=60,
            price_amount=Decimal("120.00"),
        ).booking
        session.commit()

    assert response.booking.status is BookingStatus.CANCELLED_BY_ADMIN
    assert len(response.booking.status_history) == 2
    assert response.booking.status_history[-1].old_status is BookingStatus.CONFIRMED
    assert (
        response.booking.status_history[-1].new_status
        is BookingStatus.CANCELLED_BY_ADMIN
    )
    assert saved_log is not None
    assert saved_log.status is DeliveryStatus.SENT
    assert saved_log.kind == "booking_cancelled"
    assert sender.messages[0][0] == 123
    assert "Booking cancelled" in sender.messages[0][1]
    assert "stylist unavailable" in sender.messages[0][1]
    assert second_booking.status is BookingStatus.CONFIRMED
    assert second_booking.slot_id == slot.id


def test_admin_reschedule_rejects_booked_slot_without_notification() -> None:
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    sender = FakeSender()

    with Session(engine, expire_on_commit=False) as session:
        first_client = _create_client(session)
        second_client = _create_client(session, telegram_id=456)
        original_slot = _create_slot(
            session,
            starts_at=datetime.now(UTC) + timedelta(days=1),
        )
        occupied_slot = _create_slot(
            session,
            starts_at=datetime.now(UTC) + timedelta(days=2),
        )
        booking = handle_admin_manual_booking(
            session,
            _settings(),
            telegram_user_id=111,
            client_id=first_client.id,
            slot_id=original_slot.id,
            service="coloring",
            duration_minutes=120,
            price_amount=Decimal("220.00"),
        ).booking
        handle_admin_manual_booking(
            session,
            _settings(),
            telegram_user_id=111,
            client_id=second_client.id,
            slot_id=occupied_slot.id,
            service="hair treatment",
            duration_minutes=60,
            price_amount=Decimal("120.00"),
        )
        session.commit()

        with pytest.raises(SlotUnavailableError):
            handle_admin_reschedule_booking(
                session,
                _settings(),
                sender=sender,
                telegram_user_id=111,
                booking_id=booking.id,
                new_slot_id=occupied_slot.id,
            )

        assert sender.messages == []
        assert session.scalar(select(NotificationLog)) is None
        assert booking.slot_id == original_slot.id


def test_admin_reschedule_integrity_error_becomes_slot_unavailable(monkeypatch) -> None:
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)

    with Session(engine) as session:
        client = _create_client(session)
        original_slot = _create_slot(
            session,
            starts_at=datetime.now(UTC) + timedelta(days=1),
        )
        target_slot = _create_slot(
            session,
            starts_at=datetime.now(UTC) + timedelta(days=2),
        )
        booking = handle_admin_manual_booking(
            session,
            _settings(),
            telegram_user_id=111,
            client_id=client.id,
            slot_id=original_slot.id,
            service="coloring",
            duration_minutes=120,
            price_amount=Decimal("220.00"),
        ).booking

        original_flush = session.flush
        inside_nested = {"active": False}

        @contextmanager
        def fail_inside_nested():
            inside_nested["active"] = True
            try:
                yield
            finally:
                inside_nested["active"] = False

        def fail_flush() -> None:
            if inside_nested["active"] and booking.slot is target_slot:
                raise IntegrityError(
                    "update booking slot",
                    {},
                    Exception("duplicate slot"),
                )
            original_flush()

        monkeypatch.setattr(
            booking_service,
            "_lock_available_slot",
            lambda *_: target_slot,
        )
        monkeypatch.setattr(session, "begin_nested", fail_inside_nested)
        monkeypatch.setattr(session, "flush", fail_flush)

        with pytest.raises(SlotUnavailableError):
            handle_admin_reschedule_booking(
                session,
                _settings(),
                sender=FakeSender(),
                telegram_user_id=111,
                booking_id=booking.id,
                new_slot_id=target_slot.id,
            )


def test_admin_edit_and_auth_guard() -> None:
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)

    with Session(engine, expire_on_commit=False) as session:
        client = _create_client(session)
        slot = _create_slot(session, starts_at=datetime.now(UTC) + timedelta(days=1))
        booking = handle_admin_manual_booking(
            session,
            _settings(),
            telegram_user_id=111,
            client_id=client.id,
            slot_id=slot.id,
            service="coloring",
            duration_minutes=120,
            price_amount=Decimal("220.00"),
        ).booking

        with pytest.raises(AdminAccessDenied):
            handle_admin_manual_booking(
                session,
                _settings(),
                telegram_user_id=222,
                client_id=client.id,
                slot_id=slot.id,
                service="blocked",
                duration_minutes=60,
                price_amount=Decimal("100.00"),
            )

        with pytest.raises(AdminAccessDenied):
            handle_admin_reschedule_booking(
                session,
                _settings(),
                sender=FakeSender(),
                telegram_user_id=222,
                booking_id=booking.id,
                new_slot_id=slot.id,
            )

        with pytest.raises(AdminAccessDenied):
            handle_admin_cancel_booking(
                session,
                _settings(),
                sender=FakeSender(),
                telegram_user_id=222,
                booking_id=booking.id,
            )

        with pytest.raises(AdminAccessDenied):
            handle_admin_update_booking_details(
                session,
                _settings(),
                telegram_user_id=222,
                booking_id=booking.id,
                service="hair treatment",
            )

        with pytest.raises(ValueError):
            handle_admin_update_booking_details(
                session,
                _settings(),
                telegram_user_id=111,
                booking_id=booking.id,
                service="hair treatment",
            )

        response = handle_admin_update_booking_details(
            session,
            _settings(),
            sender=FakeSender(),
            telegram_user_id=111,
            booking_id=booking.id,
            service="hair treatment",
            duration_minutes=90,
            price_amount=Decimal("180.00"),
            place="Second studio",
            notes="Updated notes",
        )
        saved_log = session.scalar(select(NotificationLog))
        session.commit()

    assert response.booking.service == "hair treatment"
    assert response.booking.duration_minutes == 90
    assert response.booking.price_amount == Decimal("180.00")
    assert response.booking.place == "Second studio"
    assert response.booking.notes == "Updated notes"
    assert response.booking.status_history[-1].new_status is BookingStatus.CONFIRMED
    assert response.notification_log is saved_log
    assert saved_log is not None
    assert saved_log.kind == "booking_updated"
    assert saved_log.status is DeliveryStatus.SENT


class FakeSender:
    def __init__(self) -> None:
        self.messages: list[tuple[int, str]] = []

    def send_message(self, recipient_telegram_id: int, text: str) -> None:
        self.messages.append((recipient_telegram_id, text))


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


def _create_client(session: Session, *, telegram_id: int = 123) -> Client:
    client = Client(
        user=User(
            telegram_id=telegram_id,
            username="test_client",
            display_name="Test Client",
        ),
        display_name="Test Client",
    )
    session.add(client)
    session.flush()
    return client


def _create_slot(session: Session, *, starts_at: datetime) -> Slot:
    slot = Slot(
        starts_at=starts_at,
        ends_at=starts_at + timedelta(hours=1),
        place="Test studio",
    )
    session.add(slot)
    session.flush()
    return slot
