from datetime import UTC, datetime, timedelta
from decimal import Decimal
from zoneinfo import ZoneInfo

from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session

from app.bot.messages import (
    admin_new_booking_message,
    booking_cancelled_message,
    booking_confirmation_message,
    booking_reminder_message,
    booking_rescheduled_message,
)
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
from app.services.notifications import send_client_notification


class FakeSender:
    def __init__(self, *, fail: bool = False) -> None:
        self.fail = fail
        self.sent_messages: list[tuple[int, str]] = []

    def send_message(self, recipient_telegram_id: int, text: str) -> None:
        if self.fail:
            raise RuntimeError("delivery failed")
        self.sent_messages.append((recipient_telegram_id, text))


def test_confirmation_message_contains_required_fields() -> None:
    booking = _booking()

    message = booking_confirmation_message(booking)

    assert "Мужская стрижка" in message
    assert "24 июня, среда" in message
    assert "10:00" in message
    assert "Test studio" in message
    assert "60 мин" in message
    assert "100 GEL" in message
    assert "Если нужно изменить запись" in message
    assert "Моя запись" in message


def test_messages_use_business_timezone() -> None:
    booking = _booking(starts_at=datetime(2026, 6, 24, 6, 0, tzinfo=UTC))

    message = booking_confirmation_message(
        booking,
        timezone=ZoneInfo("Asia/Tbilisi"),
    )

    assert "24 июня, среда" in message
    assert "10:00" in message


def test_confirmation_message_contains_yandex_and_google_location_links() -> None:
    booking = _booking()

    message = booking_confirmation_message(
        booking,
        yandex_map_url="https://yandex.example/test?a=1&b=2",
        google_map_url="https://google.example/test",
    )

    assert "Адрес: Test studio" in message
    assert '<a href="https://yandex.example/test?a=1&amp;b=2">Yandex</a>' in message
    assert '<a href="https://google.example/test">Google</a>' in message


def test_change_notifications_contain_required_fields() -> None:
    booking = _booking()

    rescheduled = booking_rescheduled_message(booking)
    cancelled = booking_cancelled_message(booking, reason="client request")

    for message in (rescheduled, cancelled):
        assert "Мужская стрижка" in message
        assert "24 июня, среда" in message
        assert "10:00" in message
        assert "Test studio" in message

    assert "Запись перенесена" in rescheduled
    assert "Запись отменена" in cancelled
    assert "client request" in cancelled


def test_admin_new_booking_message_contains_required_fields() -> None:
    booking = _booking(starts_at=datetime(2026, 6, 24, 6, 0, tzinfo=UTC))

    message = admin_new_booking_message(booking, timezone=ZoneInfo("Asia/Tbilisi"))

    assert "Новая запись" in message
    assert "Мужская стрижка" in message
    assert "24 июня, среда" in message
    assert "10:00" in message
    assert "Test studio" in message
    assert "100 GEL" in message
    assert "Test User" in message
    assert "ID клиента:" in message
    assert "tg://user?id=123" in message


def test_reminder_message_contains_required_fields_and_location_links() -> None:
    booking = _booking(starts_at=datetime(2026, 6, 27, 6, 0, tzinfo=UTC))

    message = booking_reminder_message(
        booking,
        reminder_kind="24h",
        timezone=ZoneInfo("Asia/Tbilisi"),
        yandex_map_url="https://yandex.example/test",
        google_map_url="https://google.example/test",
    )

    assert "Напоминание: запись завтра" in message
    assert "Мужская стрижка" in message
    assert "27 июня, суббота" in message
    assert "10:00" in message
    assert "Адрес: Test studio" in message
    assert '<a href="https://yandex.example/test">Yandex</a>' in message
    assert '<a href="https://google.example/test">Google</a>' in message
    assert "Моя запись" in message


def test_notification_delivery_is_logged() -> None:
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)

    with Session(engine, expire_on_commit=False) as session:
        booking = _persist_booking(session)
        sender = FakeSender()

        success_log = send_client_notification(
            session,
            sender=sender,
            booking=booking,
            kind="booking_confirmation",
            text=booking_confirmation_message(booking),
        )
        session.commit()

        failure_sender = FakeSender(fail=True)
        failure_log = send_client_notification(
            session,
            sender=failure_sender,
            booking=booking,
            kind="booking_rescheduled",
            text=booking_rescheduled_message(booking),
        )
        session.commit()

        logs = session.scalars(
            select(NotificationLog).order_by(NotificationLog.id)
        ).all()

    assert sender.sent_messages == [(123, booking_confirmation_message(booking))]
    assert success_log.status is DeliveryStatus.SENT
    assert success_log.sent_at is not None
    assert failure_log.status is DeliveryStatus.FAILED
    assert failure_log.error == "delivery failed"
    assert [log.status for log in logs] == [DeliveryStatus.SENT, DeliveryStatus.FAILED]


def test_notification_without_telegram_identity_is_logged_failed() -> None:
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)

    with Session(engine, expire_on_commit=False) as session:
        booking = _persist_booking(session, with_user=False)
        sender = FakeSender()

        log = send_client_notification(
            session,
            sender=sender,
            booking=booking,
            kind="booking_confirmation",
            text=booking_confirmation_message(booking),
        )
        session.commit()

    assert sender.sent_messages == []
    assert log.status is DeliveryStatus.FAILED
    assert log.recipient_telegram_id is None
    assert log.error == "Client has no Telegram identity"


def _booking(*, starts_at: datetime | None = None) -> Booking:
    starts_at = starts_at or datetime(2026, 6, 24, 6, 0, tzinfo=UTC)
    return Booking(
        id=1,
        client=Client(user=User(telegram_id=123), display_name="Test User"),
        slot=Slot(
            starts_at=starts_at,
            ends_at=starts_at + timedelta(hours=1),
            place="Test studio",
        ),
        service="haircut_male",
        starts_at=starts_at,
        ends_at=starts_at + timedelta(hours=1),
        duration_minutes=60,
        place="Test studio",
        price_amount=Decimal("100.00"),
        status=BookingStatus.CONFIRMED,
    )


def _persist_booking(session: Session, *, with_user: bool = True) -> Booking:
    booking = _booking()
    booking.id = None
    booking.slot_id = None
    if not with_user:
        booking.client.user = None
    session.add(booking)
    session.flush()
    return booking
