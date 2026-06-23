"""Thin scheduler adapter for reminder recovery."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from datetime import UTC, datetime

from sqlalchemy.orm import Session

from app.services.reminders import rebuild_reminder_logs


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


def _as_utc(value: datetime) -> datetime:
    if value.tzinfo is None:
        return value.replace(tzinfo=UTC)
    return value.astimezone(UTC)
