from datetime import UTC, datetime, timedelta
from decimal import Decimal

import pytest
from sqlalchemy import create_engine
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

import app.services.booking as booking_service
from app.db.models import Base, BookingStatus, Client, Slot, User
from app.services.booking import (
    DEFAULT_HAIRCUT_DURATION_MINUTES,
    DEFAULT_HAIRCUT_PRICE,
    SlotUnavailableError,
    UnsupportedSelfBookServiceError,
    create_haircut_booking,
    create_manual_booking,
    create_simple_booking,
    list_available_slots,
)


def test_create_haircut_booking() -> None:
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    starts_at = datetime.now(UTC) + timedelta(days=1)

    with Session(engine, expire_on_commit=False) as session:
        client = _create_client(session)
        slot = _create_slot(session, starts_at=starts_at)

        booking = create_haircut_booking(
            session,
            client_id=client.id,
            slot_id=slot.id,
        )
        session.commit()

    assert booking.status is BookingStatus.CONFIRMED
    assert booking.service == "haircut"
    assert booking.price_amount == DEFAULT_HAIRCUT_PRICE
    assert booking.duration_minutes == DEFAULT_HAIRCUT_DURATION_MINUTES
    assert booking.starts_at == starts_at
    assert booking.ends_at == starts_at + timedelta(hours=1)
    assert booking.place == "Test studio"
    assert len(booking.status_history) == 1


def test_prevent_double_booking(tmp_path) -> None:
    engine = create_engine(f"sqlite:///{tmp_path / 'booking.db'}")
    Base.metadata.create_all(engine)
    starts_at = datetime.now(UTC) + timedelta(days=1)

    with Session(engine, expire_on_commit=False) as session:
        first_client = _create_client(session, telegram_id=101)
        second_client = _create_client(session, telegram_id=202)
        slot = _create_slot(session, starts_at=starts_at)
        create_haircut_booking(session, client_id=first_client.id, slot_id=slot.id)
        session.commit()

    with Session(engine) as session, pytest.raises(SlotUnavailableError):
        create_haircut_booking(
            session,
            client_id=second_client.id,
            slot_id=slot.id,
        )


def test_coloring_not_self_bookable() -> None:
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    starts_at = datetime.now(UTC) + timedelta(days=1)

    with Session(engine) as session:
        client = _create_client(session)
        slot = _create_slot(session, starts_at=starts_at)

        with pytest.raises(UnsupportedSelfBookServiceError):
            create_simple_booking(
                session,
                client_id=client.id,
                slot_id=slot.id,
                service="coloring",
            )


def test_past_slot_is_unavailable() -> None:
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    starts_at = datetime.now(UTC) - timedelta(days=1)

    with Session(engine) as session:
        client = _create_client(session)
        slot = _create_slot(session, starts_at=starts_at)

        with pytest.raises(SlotUnavailableError):
            create_haircut_booking(session, client_id=client.id, slot_id=slot.id)


def test_blocked_slot_is_unavailable() -> None:
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    starts_at = datetime.now(UTC) + timedelta(days=1)

    with Session(engine) as session:
        client = _create_client(session)
        slot = _create_slot(session, starts_at=starts_at, is_blocked=True)

        with pytest.raises(SlotUnavailableError):
            create_haircut_booking(session, client_id=client.id, slot_id=slot.id)


def test_list_available_slots_filters_unavailable_slots() -> None:
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    now = datetime.now(UTC)

    with Session(engine, expire_on_commit=False) as session:
        client = _create_client(session)
        available = _create_slot(session, starts_at=now + timedelta(days=1))
        blocked = _create_slot(
            session,
            starts_at=now + timedelta(days=2),
            is_blocked=True,
        )
        past = _create_slot(session, starts_at=now - timedelta(days=1))
        booked = _create_slot(session, starts_at=now + timedelta(days=3))
        create_haircut_booking(session, client_id=client.id, slot_id=booked.id)
        session.commit()

        available_slots = list_available_slots(session, now=now)

    assert available_slots == [available]
    assert blocked not in available_slots
    assert past not in available_slots
    assert booked not in available_slots


def test_manual_long_booking_blocks_overlapping_haircut_slots() -> None:
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    now = datetime.now(UTC)
    first_start = now + timedelta(days=1)

    with Session(engine, expire_on_commit=False) as session:
        admin_client = _create_client(session, telegram_id=101)
        haircut_client = _create_client(session, telegram_id=202)
        start_slot = _create_slot(session, starts_at=first_start)
        overlap_one = _create_slot(session, starts_at=first_start + timedelta(hours=1))
        overlap_two = _create_slot(session, starts_at=first_start + timedelta(hours=2))
        after_manual = _create_slot(session, starts_at=first_start + timedelta(hours=3))

        manual = create_manual_booking(
            session,
            client_id=admin_client.id,
            slot_id=start_slot.id,
            service="coloring",
            duration_minutes=180,
            price_amount=Decimal("250.00"),
        )
        session.commit()

        available_slots = list_available_slots(session, now=now)

        with pytest.raises(SlotUnavailableError):
            create_haircut_booking(
                session,
                client_id=haircut_client.id,
                slot_id=overlap_one.id,
            )

    assert manual.ends_at == first_start + timedelta(hours=3)
    assert available_slots == [after_manual]
    assert overlap_one not in available_slots
    assert overlap_two not in available_slots


def test_integrity_error_does_not_call_session_rollback(monkeypatch) -> None:
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    starts_at = datetime.now(UTC) + timedelta(days=1)

    with Session(engine) as session:
        client = _create_client(session)
        slot = _create_slot(session, starts_at=starts_at)

        def fail_flush() -> None:
            raise IntegrityError("insert booking", {}, Exception("duplicate slot"))

        def fail_rollback() -> None:
            raise AssertionError("service must not roll back caller-owned session")

        monkeypatch.setattr(booking_service, "_lock_available_slot", lambda *_: slot)
        monkeypatch.setattr(session, "flush", fail_flush)
        monkeypatch.setattr(session, "rollback", fail_rollback)

        with pytest.raises(SlotUnavailableError):
            create_haircut_booking(session, client_id=client.id, slot_id=slot.id)


def _create_client(
    session: Session,
    *,
    telegram_id: int = 123,
) -> Client:
    user = User(telegram_id=telegram_id, display_name="Test User")
    client = Client(user=user, display_name="Test User")
    session.add(client)
    session.flush()
    return client


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
