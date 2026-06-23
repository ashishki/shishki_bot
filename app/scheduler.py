"""Reminder scheduler adapters and runtime delivery job."""

from __future__ import annotations

import asyncio
from collections.abc import Callable
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any
from zoneinfo import ZoneInfo

from apscheduler.schedulers.background import BackgroundScheduler
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from app.bot.messages import booking_reminder_message
from app.config import Settings
from app.db.models import ReminderLog
from app.services.notifications import NotificationSender
from app.services.reminders import (
    rebuild_reminder_logs,
    recover_pending_reminders,
    send_due_reminder,
)

DEFAULT_REMINDER_TIMEZONE = ZoneInfo("Asia/Tbilisi")


@dataclass(frozen=True, slots=True)
class ReminderJob:
    reminder_log_id: int
    booking_id: int
    reminder_kind: str
    scheduled_for: datetime


def rebuild_reminder_jobs(
    session_factory: Callable[[], Session],
    *,
    now: datetime | None = None,
) -> list[ReminderJob]:
    with session_factory() as session:
        reminders = rebuild_reminder_logs(session, now=now)
        jobs = [
            ReminderJob(
                reminder_log_id=reminder.id,
                booking_id=reminder.booking_id,
                reminder_kind=reminder.reminder_kind,
                scheduled_for=_as_utc(reminder.scheduled_for),
            )
            for reminder in reminders
            if reminder.id is not None
        ]
        session.commit()
        return jobs


def rebuild_due_reminder_jobs(
    session_factory: Callable[[], Session],
    *,
    now: datetime | None = None,
) -> list[ReminderJob]:
    cutoff = now or datetime.now(UTC)
    return [
        job
        for job in rebuild_reminder_jobs(session_factory, now=now)
        if job.scheduled_for <= cutoff
    ]


class ThreadsafeTelegramSender:
    """Synchronous notification sender for scheduler worker threads."""

    def __init__(
        self,
        bot: Any,
        loop: asyncio.AbstractEventLoop,
        *,
        timeout_seconds: int = 30,
    ) -> None:
        self._bot = bot
        self._loop = loop
        self._timeout_seconds = timeout_seconds

    def send_message(self, recipient_telegram_id: int, text: str) -> None:
        future = asyncio.run_coroutine_threadsafe(
            self._bot.send_message(recipient_telegram_id, text),
            self._loop,
        )
        future.result(timeout=self._timeout_seconds)


def start_reminder_scheduler(
    settings: Settings,
    *,
    bot: Any,
    loop: asyncio.AbstractEventLoop,
    interval_seconds: int = 60,
) -> BackgroundScheduler:
    session_factory = _sync_session_factory(settings.database_url)
    sender = ThreadsafeTelegramSender(bot, loop)
    scheduler = BackgroundScheduler(timezone=UTC)
    scheduler.add_job(
        send_due_reminders,
        "interval",
        seconds=interval_seconds,
        args=(session_factory, settings, sender),
        id="send_due_reminders",
        replace_existing=True,
        coalesce=True,
        max_instances=1,
        next_run_time=datetime.now(UTC),
    )
    scheduler.start()
    return scheduler


def send_due_reminders(
    session_factory: Callable[[], Session],
    settings: Settings,
    sender: NotificationSender,
    *,
    now: datetime | None = None,
) -> tuple[int, ...]:
    sent_or_attempted: list[int] = []
    with session_factory() as session:
        reminders = recover_pending_reminders(session, now=now)
        for reminder in reminders:
            text = _reminder_text(reminder, settings)
            send_due_reminder(
                session,
                sender=sender,
                reminder_log=reminder,
                text=text,
            )
            if reminder.id is not None:
                sent_or_attempted.append(reminder.id)
        session.commit()
    return tuple(sent_or_attempted)


def _as_utc(value: datetime) -> datetime:
    if value.tzinfo is None:
        return value.replace(tzinfo=DEFAULT_REMINDER_TIMEZONE).astimezone(UTC)
    return value.astimezone(UTC)


def _reminder_text(reminder: ReminderLog, settings: Settings) -> str:
    return booking_reminder_message(
        reminder.booking,
        reminder_kind=reminder.reminder_kind,
        timezone=settings.timezone_info,
        yandex_map_url=settings.yandex_map_url,
        google_map_url=settings.google_map_url,
        default_map_url=settings.default_map_url,
    )


def _sync_session_factory(database_url: str) -> sessionmaker[Session]:
    sync_url = _sync_database_url(database_url)
    engine = create_engine(sync_url)
    return sessionmaker(engine, expire_on_commit=False)


def _sync_database_url(database_url: str) -> str:
    if database_url.startswith("sqlite+aiosqlite:///"):
        return "sqlite:///" + database_url.removeprefix("sqlite+aiosqlite:///")
    if database_url.startswith("sqlite+aiosqlite://"):
        return "sqlite://" + database_url.removeprefix("sqlite+aiosqlite://")
    return database_url
