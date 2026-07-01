from datetime import UTC, datetime, timedelta
from decimal import Decimal
from pathlib import Path

import pytest
from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session, sessionmaker

from app.config import Settings
from app.db.models import (
    Base,
    Booking,
    BookingStatus,
    Client,
    DeliveryStatus,
    ReminderLog,
    Slot,
    User,
)
from app.scheduler import (
    rebuild_due_reminder_jobs,
    rebuild_reminder_jobs,
    send_due_reminders,
)
from app.services.reminders import (
    REMINDER_3H,
    REMINDER_24H,
    ReminderSchedule,
    calculate_reminder_times,
    ensure_reminder_log,
    recover_pending_reminders,
    send_due_reminder,
)


def test_reminder_times() -> None:
    booking = _booking_for(datetime(2026, 6, 24, 12, 0, tzinfo=UTC))

    schedules = calculate_reminder_times(booking)

    assert tuple(schedule.reminder_kind for schedule in schedules) == (
        REMINDER_24H,
        REMINDER_3H,
    )
    assert tuple(schedule.scheduled_for for schedule in schedules) == (
        datetime(2026, 6, 23, 12, 0, tzinfo=UTC),
        datetime(2026, 6, 24, 9, 0, tzinfo=UTC),
    )


def test_naive_sqlite_times_are_treated_as_business_timezone() -> None:
    booking = _booking_for(datetime(2026, 6, 27, 13, 0))

    schedules = calculate_reminder_times(booking)

    assert tuple(schedule.scheduled_for for schedule in schedules) == (
        datetime(2026, 6, 26, 13, 0),
        datetime(2026, 6, 27, 10, 0),
    )


def test_recover_pending_reminders() -> None:
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    now = datetime(2026, 6, 23, 13, 0, tzinfo=UTC)

    with Session(engine, expire_on_commit=False) as session:
        due_booking = _create_booking(
            session,
            starts_at=datetime(2026, 6, 24, 12, 0, tzinfo=UTC),
        )
        not_due_booking = _create_booking(
            session,
            telegram_id=456,
            starts_at=datetime(2026, 6, 24, 18, 0, tzinfo=UTC),
        )
        session.commit()

        pending = recover_pending_reminders(session, now=now)
        session.commit()

        saved_logs = session.scalars(select(ReminderLog)).all()

    assert len(pending) == 1
    assert pending[0].booking_id == due_booking.id
    assert pending[0].reminder_kind == REMINDER_24H
    assert pending[0].status is DeliveryStatus.PENDING
    assert len(saved_logs) == 4
    assert due_booking.id in {log.booking_id for log in saved_logs}
    assert not_due_booking.id in {log.booking_id for log in saved_logs}


def test_scheduler_rebuilds_future_and_due_jobs_without_detached_orm() -> None:
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    factory = sessionmaker(engine)
    now = datetime(2026, 6, 23, 13, 0, tzinfo=UTC)

    with factory() as session:
        booking = _create_booking(
            session,
            starts_at=datetime(2026, 6, 24, 12, 0, tzinfo=UTC),
        )
        session.commit()
        booking_id = booking.id

    all_jobs = rebuild_reminder_jobs(factory, now=now)
    due_jobs = rebuild_due_reminder_jobs(factory, now=now)

    assert len(all_jobs) == 2
    assert len(due_jobs) == 1
    assert all(job.booking_id == booking_id for job in all_jobs)
    assert {job.reminder_kind for job in all_jobs} == {REMINDER_24H, REMINDER_3H}
    assert due_jobs[0].reminder_kind == REMINDER_24H


def test_scheduler_job_sends_due_reminders() -> None:
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    factory = sessionmaker(engine, expire_on_commit=False)
    sender = FakeSender()
    now = datetime(2026, 6, 23, 13, 0, tzinfo=UTC)

    with factory() as session:
        booking = _create_booking(
            session,
            starts_at=datetime(2026, 6, 24, 12, 0, tzinfo=UTC),
        )
        session.commit()
        booking_id = booking.id

    attempted = send_due_reminders(
        factory,
        _settings(),
        sender,
        now=now,
    )

    with factory() as session:
        logs = session.scalars(
            select(ReminderLog).order_by(ReminderLog.reminder_kind)
        ).all()

    assert len(attempted) == 1
    assert sender.messages[0][0] == 123
    assert "Напоминание: запись завтра" in sender.messages[0][1]
    assert "Стрижка" in sender.messages[0][1]
    assert "Test studio" in sender.messages[0][1]
    assert {log.booking_id for log in logs} == {booking_id}
    assert [log.status for log in logs] == [
        DeliveryStatus.SENT,
        DeliveryStatus.PENDING,
    ]


def test_scheduler_job_sends_naive_local_due_reminders() -> None:
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    factory = sessionmaker(engine, expire_on_commit=False)
    sender = FakeSender()

    with factory() as session:
        booking = _create_booking(
            session,
            starts_at=datetime(2026, 6, 27, 13, 0),
        )
        session.commit()
        booking_id = booking.id

    attempted = send_due_reminders(
        factory,
        _settings(),
        sender,
        now=datetime(2026, 6, 26, 9, 1, tzinfo=UTC),
    )

    with factory() as session:
        logs = session.scalars(
            select(ReminderLog).order_by(ReminderLog.reminder_kind)
        ).all()

    assert len(attempted) == 1
    assert sender.messages[0][0] == 123
    assert "Напоминание: запись завтра" in sender.messages[0][1]
    assert "\n13:00\n" in sender.messages[0][1]
    assert "\n17:00\n" not in sender.messages[0][1]
    assert {log.booking_id for log in logs} == {booking_id}
    assert [log.scheduled_for for log in logs] == [
        datetime(2026, 6, 26, 13, 0),
        datetime(2026, 6, 27, 10, 0),
    ]
    assert [log.status for log in logs] == [
        DeliveryStatus.SENT,
        DeliveryStatus.PENDING,
    ]


def test_no_duplicate_reminders() -> None:
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    now = datetime(2026, 6, 23, 13, 0, tzinfo=UTC)
    sender = FakeSender()

    with Session(engine, expire_on_commit=False) as session:
        booking = _create_booking(
            session,
            starts_at=datetime(2026, 6, 24, 12, 0, tzinfo=UTC),
        )
        sent_log = ReminderLog(
            booking=booking,
            reminder_kind=REMINDER_24H,
            scheduled_for=datetime(2026, 6, 23, 12, 0, tzinfo=UTC),
            status=DeliveryStatus.SENT,
            sent_at=datetime(2026, 6, 23, 12, 0, tzinfo=UTC),
        )
        session.add(sent_log)
        session.commit()

        pending = recover_pending_reminders(session, now=now)
        send_due_reminder(
            session,
            sender=sender,
            reminder_log=sent_log,
            text="Reminder",
        )
        session.commit()

        logs = session.scalars(select(ReminderLog)).all()

    assert pending == []
    assert sender.messages == []
    assert len(logs) == 2
    assert sent_log.status is DeliveryStatus.SENT


def test_sent_reminder_is_not_recovered_after_restart() -> None:
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    now = datetime(2026, 6, 23, 13, 0, tzinfo=UTC)

    with Session(engine, expire_on_commit=False) as session:
        booking = _create_booking(
            session,
            starts_at=datetime(2026, 6, 24, 12, 0, tzinfo=UTC),
        )
        session.add(
            ReminderLog(
                booking=booking,
                reminder_kind=REMINDER_24H,
                scheduled_for=datetime(2026, 6, 23, 12, 0, tzinfo=UTC),
                status=DeliveryStatus.SENT,
                sent_at=datetime(2026, 6, 23, 12, 0, tzinfo=UTC),
            )
        )
        session.commit()

    with Session(engine, expire_on_commit=False) as restarted_session:
        pending = recover_pending_reminders(restarted_session, now=now)
        logs = restarted_session.scalars(select(ReminderLog)).all()

    assert pending == []
    assert len(logs) == 2
    assert [log.status for log in logs if log.reminder_kind == REMINDER_24H] == [
        DeliveryStatus.SENT
    ]


def test_stale_second_session_does_not_send_duplicate_reminder(
    tmp_path: Path,
) -> None:
    engine = create_engine(f"sqlite:///{tmp_path / 'reminders.db'}")
    Base.metadata.create_all(engine)
    factory = sessionmaker(engine, expire_on_commit=False)
    sender_one = FakeSender()
    sender_two = FakeSender()

    with factory() as session:
        booking = _create_booking(
            session,
            starts_at=datetime(2026, 6, 24, 12, 0, tzinfo=UTC),
        )
        reminder = ensure_reminder_log(
            session,
            booking=booking,
            schedule=ReminderSchedule(
                reminder_kind=REMINDER_24H,
                scheduled_for=datetime(2026, 6, 23, 12, 0, tzinfo=UTC),
            ),
        )
        session.commit()
        reminder_id = reminder.id

    with factory() as first_session, factory() as second_session:
        first_log = first_session.get(ReminderLog, reminder_id)
        second_log = second_session.get(ReminderLog, reminder_id)
        assert first_log is not None
        assert second_log is not None

        send_due_reminder(
            first_session,
            sender=sender_one,
            reminder_log=first_log,
            text="Reminder",
        )
        first_session.commit()
        send_due_reminder(
            second_session,
            sender=sender_two,
            reminder_log=second_log,
            text="Reminder",
        )
        second_session.commit()

    assert sender_one.messages == [(123, "Reminder")]
    assert sender_two.messages == []
    assert second_log.status is DeliveryStatus.SENT


def test_unique_race_recovery_keeps_session_committable(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)

    with Session(engine, expire_on_commit=False) as session:
        booking = _create_booking(
            session,
            starts_at=datetime(2026, 6, 24, 12, 0, tzinfo=UTC),
        )
        existing_log = ReminderLog(
            booking=booking,
            reminder_kind=REMINDER_24H,
            scheduled_for=datetime(2026, 6, 23, 12, 0, tzinfo=UTC),
            status=DeliveryStatus.PENDING,
        )
        session.add(existing_log)
        session.commit()
        existing_id = existing_log.id

        original_scalar = session.scalar
        scalar_calls = 0

        def scalar_with_race(statement, *args, **kwargs):
            nonlocal scalar_calls
            scalar_calls += 1
            if scalar_calls == 1:
                return None
            return original_scalar(statement, *args, **kwargs)

        monkeypatch.setattr(session, "scalar", scalar_with_race)

        recovered_log = ensure_reminder_log(
            session,
            booking=booking,
            schedule=ReminderSchedule(
                reminder_kind=REMINDER_24H,
                scheduled_for=datetime(2026, 6, 23, 12, 0, tzinfo=UTC),
            ),
        )
        session.commit()

        saved_logs = session.scalars(select(ReminderLog)).all()

    assert recovered_log.id == existing_id
    assert len(saved_logs) == 1
    assert scalar_calls >= 2


def test_rescheduled_booking_reconciles_pending_and_sent_reminders() -> None:
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)

    with Session(engine, expire_on_commit=False) as session:
        booking = _create_booking(
            session,
            starts_at=datetime(2026, 6, 24, 12, 0, tzinfo=UTC),
            status=BookingStatus.RESCHEDULED,
        )
        old_sent_log = ReminderLog(
            booking=booking,
            reminder_kind=REMINDER_24H,
            scheduled_for=datetime(2026, 6, 23, 12, 0, tzinfo=UTC),
            status=DeliveryStatus.SENT,
            sent_at=datetime(2026, 6, 23, 12, 1, tzinfo=UTC),
        )
        old_pending_log = ReminderLog(
            booking=booking,
            reminder_kind=REMINDER_3H,
            scheduled_for=datetime(2026, 6, 24, 9, 0, tzinfo=UTC),
            status=DeliveryStatus.PENDING,
        )
        session.add_all([old_sent_log, old_pending_log])
        session.commit()

        booking.starts_at = datetime(2026, 6, 25, 12, 0, tzinfo=UTC)
        booking.ends_at = datetime(2026, 6, 25, 13, 0, tzinfo=UTC)
        logs = recover_pending_reminders(
            session,
            now=datetime(2026, 6, 24, 13, 0, tzinfo=UTC),
        )

    assert len(logs) == 1
    assert old_sent_log.scheduled_for == datetime(2026, 6, 24, 12, 0, tzinfo=UTC)
    assert old_sent_log.status is DeliveryStatus.PENDING
    assert old_sent_log.sent_at is None
    assert old_pending_log.scheduled_for == datetime(2026, 6, 25, 9, 0, tzinfo=UTC)


def test_inactive_booking_reminder_is_skipped_at_send_time() -> None:
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    sender = FakeSender()

    with Session(engine, expire_on_commit=False) as session:
        booking = _create_booking(
            session,
            starts_at=datetime(2026, 6, 24, 12, 0, tzinfo=UTC),
            status=BookingStatus.CANCELLED_BY_ADMIN,
        )
        reminder = ReminderLog(
            booking=booking,
            reminder_kind=REMINDER_24H,
            scheduled_for=datetime(2026, 6, 23, 12, 0, tzinfo=UTC),
            status=DeliveryStatus.PENDING,
        )
        session.add(reminder)
        session.commit()

        send_due_reminder(
            session,
            sender=sender,
            reminder_log=reminder,
            text="Reminder",
        )

    assert reminder.status is DeliveryStatus.SKIPPED
    assert reminder.error == "Booking is no longer active"
    assert sender.messages == []


def test_failed_reminder_is_recovered_for_retry() -> None:
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)

    with Session(engine, expire_on_commit=False) as session:
        booking = _create_booking(
            session,
            starts_at=datetime(2026, 6, 24, 12, 0, tzinfo=UTC),
        )
        failed_log = ReminderLog(
            booking=booking,
            reminder_kind=REMINDER_24H,
            scheduled_for=datetime(2026, 6, 23, 12, 0, tzinfo=UTC),
            status=DeliveryStatus.FAILED,
            error="temporary failure",
        )
        session.add(failed_log)
        session.commit()

        pending = recover_pending_reminders(
            session,
            now=datetime(2026, 6, 23, 13, 0, tzinfo=UTC),
        )

    assert pending == [failed_log]


def test_async_sender_is_logged_failed() -> None:
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)

    with Session(engine, expire_on_commit=False) as session:
        booking = _create_booking(
            session,
            starts_at=datetime(2026, 6, 24, 12, 0, tzinfo=UTC),
        )
        reminder = ensure_reminder_log(
            session,
            booking=booking,
            schedule=ReminderSchedule(
                reminder_kind=REMINDER_24H,
                scheduled_for=datetime(2026, 6, 23, 12, 0, tzinfo=UTC),
            ),
        )

        send_due_reminder(
            session,
            sender=AsyncLikeSender(),
            reminder_log=reminder,
            text="Reminder",
        )

    assert reminder.status is DeliveryStatus.FAILED
    assert reminder.error == "NotificationSender.send_message must be synchronous"


class FakeSender:
    def __init__(self) -> None:
        self.messages: list[tuple[int, str]] = []

    def send_message(self, recipient_telegram_id: int, text: str) -> None:
        self.messages.append((recipient_telegram_id, text))


class AsyncLikeSender:
    async def send_message(self, recipient_telegram_id: int, text: str) -> None:
        return None


def _booking_for(starts_at: datetime) -> Booking:
    slot = Slot(
        starts_at=starts_at,
        ends_at=starts_at + timedelta(hours=1),
        place="Test studio",
    )
    return Booking(
        client=Client(user=User(telegram_id=123), display_name="Test Client"),
        slot=slot,
        service="haircut",
        starts_at=starts_at,
        ends_at=starts_at + timedelta(hours=1),
        duration_minutes=60,
        place="Test studio",
        price_amount=Decimal("90.00"),
        status=BookingStatus.CONFIRMED,
    )


def _create_booking(
    session: Session,
    *,
    starts_at: datetime,
    telegram_id: int = 123,
    status: BookingStatus = BookingStatus.CONFIRMED,
) -> Booking:
    booking = _booking_for(starts_at)
    booking.client.user.telegram_id = telegram_id
    booking.status = status
    session.add(booking)
    session.flush()
    return booking


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
