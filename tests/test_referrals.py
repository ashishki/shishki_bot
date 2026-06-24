from datetime import UTC, datetime, timedelta
from decimal import Decimal

from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session, sessionmaker

from app.bot.handlers.admin import (
    handle_admin_client_card_view,
    handle_admin_mark_referral_bonus_awarded,
    handle_admin_referral_bonuses,
)
from app.bot.handlers.client import handle_start_payload
from app.config import Settings
from app.db.models import (
    Base,
    Booking,
    BookingStatus,
    Client,
    Referral,
    ReferralBonus,
    ReferralBonusStatus,
    ReferralStatus,
    Slot,
    User,
)
from app.scheduler import send_pending_referral_bonus_reminders
from app.services.finance import complete_booking
from app.services.referrals import (
    REFERRAL_REWARD_LABEL,
    ensure_referral_code,
    pending_referral_bonuses,
    referral_progress,
    register_referral_start,
)


def test_referral_qualifies_bonus_after_three_completed_referred_visits() -> None:
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)

    with Session(engine, expire_on_commit=False) as session:
        referrer = _create_client(session, telegram_id=100, display_name="Referrer")
        code = ensure_referral_code(session, client_id=referrer.id)

        for index in range(3):
            referred = _create_client(
                session,
                telegram_id=200 + index,
                display_name=f"Friend {index}",
            )
            registration = register_referral_start(
                session,
                referral_code=code.code,
                referred_client_id=referred.id,
            )
            booking = _create_booking(
                session,
                client=referred,
                starts_at=datetime(2026, 6, 25 + index, 10, 0, tzinfo=UTC),
            )
            complete_booking(
                session,
                booking_id=booking.id,
                final_amount=Decimal("90.00"),
            )

            assert registration.registered

        session.commit()

        referrals = session.scalars(select(Referral)).all()
        bonuses = pending_referral_bonuses(session)
        progress = referral_progress(session, client_id=referrer.id)

    assert [referral.status for referral in referrals] == [
        ReferralStatus.QUALIFIED,
        ReferralStatus.QUALIFIED,
        ReferralStatus.QUALIFIED,
    ]
    assert len(bonuses) == 1
    assert bonuses[0].client_id == referrer.id
    assert bonuses[0].referral_count == 3
    assert bonuses[0].reward_label == REFERRAL_REWARD_LABEL
    assert progress.qualified_count == 3
    assert progress.pending_bonus_count == 1


def test_referral_ignores_self_referral_and_existing_clients() -> None:
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)

    with Session(engine, expire_on_commit=False) as session:
        referrer = _create_client(session, telegram_id=100, display_name="Referrer")
        code = ensure_referral_code(session, client_id=referrer.id)
        existing = _create_client(session, telegram_id=200, display_name="Existing")
        _create_booking(
            session,
            client=existing,
            starts_at=datetime(2026, 6, 25, 10, 0, tzinfo=UTC),
        )

        self_result = register_referral_start(
            session,
            referral_code=code.code,
            referred_client_id=referrer.id,
        )
        existing_result = register_referral_start(
            session,
            referral_code=code.code,
            referred_client_id=existing.id,
        )
        session.commit()

        progress = referral_progress(session, client_id=referrer.id)

    assert not self_result.registered
    assert self_result.reason == "self referral ignored"
    assert not existing_result.registered
    assert existing_result.reason == "existing client ignored"
    assert progress.qualified_count == 0
    assert progress.pending_count == 0


def test_client_start_payload_records_referral_before_booking() -> None:
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    now = datetime(2026, 6, 24, 10, 0, tzinfo=UTC)

    with Session(engine, expire_on_commit=False) as session:
        referrer = _create_client(session, telegram_id=100, display_name="Referrer")
        code = ensure_referral_code(session, client_id=referrer.id)
        _create_slot(session, starts_at=now + timedelta(days=1))
        session.commit()

        response = handle_start_payload(
            session,
            _settings(),
            telegram_user_id=777,
            display_name="New Client",
            username="new_client",
            start_payload=f"ref_{code.code}",
            now=now,
        )
        assert response.should_commit
        session.commit()

        referral = session.scalar(select(Referral))

    assert "Рекомендация сохранена" in response.text
    assert referral is not None
    assert referral.referrer_client_id == referrer.id
    assert referral.status is ReferralStatus.PENDING


def test_admin_card_bonus_list_and_award_action() -> None:
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)

    with Session(engine, expire_on_commit=False) as session:
        referrer = _client_with_pending_bonus(session)
        session.commit()

        card = handle_admin_client_card_view(
            session,
            _settings(),
            telegram_user_id=111,
            client_id=referrer.id,
            now=datetime(2026, 7, 1, 10, 0, tzinfo=UTC),
        )
        bonuses = handle_admin_referral_bonuses(
            session,
            _settings(),
            telegram_user_id=111,
        )
        bonus = session.scalar(select(ReferralBonus))
        awarded = handle_admin_mark_referral_bonus_awarded(
            session,
            _settings(),
            telegram_user_id=111,
            bonus_id=bonus.id,
        )
        session.commit()

        saved_bonus = session.get(ReferralBonus, bonus.id)

    assert "Рекомендации:" in card.text
    assert "Засчитано: 3/3" in card.text
    assert "Бонусов к выдаче: 1" in card.text
    assert "Бонусы к выдаче" in bonuses.text
    assert "профессиональная косметика" in bonuses.text
    assert "Бонус #" in awarded.text
    assert saved_bonus.status is ReferralBonusStatus.AWARDED
    assert saved_bonus.awarded_at is not None


def test_scheduler_sends_referral_bonus_reminder_once() -> None:
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    factory = sessionmaker(engine, expire_on_commit=False)
    sender = FakeSender()
    now = datetime(2026, 7, 1, 10, 0, tzinfo=UTC)

    with factory() as session:
        referrer = _client_with_pending_bonus(session)
        session.commit()
        bonus_id = session.scalar(select(ReferralBonus).limit(1)).id
        referrer_id = referrer.id

    notified = send_pending_referral_bonus_reminders(
        factory,
        _settings(),
        sender,
        now=now,
    )
    notified_again = send_pending_referral_bonus_reminders(
        factory,
        _settings(),
        sender,
        now=now + timedelta(minutes=1),
    )

    with factory() as session:
        bonus = session.get(ReferralBonus, bonus_id)
        progress = referral_progress(session, client_id=referrer_id)

    assert notified == (bonus_id,)
    assert notified_again == ()
    assert sender.messages == [
        (
            111,
            sender.messages[0][1],
        )
    ]
    assert "Бонус за рекомендации" in sender.messages[0][1]
    assert "профессиональная косметика" in sender.messages[0][1]
    assert bonus.notification_sent_at.replace(tzinfo=UTC) == now
    assert progress.pending_bonus_count == 1


class FakeSender:
    def __init__(self) -> None:
        self.messages: list[tuple[int, str]] = []

    def send_message(self, recipient_telegram_id: int, text: str) -> None:
        self.messages.append((recipient_telegram_id, text))


def _client_with_pending_bonus(session: Session) -> Client:
    referrer = _create_client(session, telegram_id=100, display_name="Referrer")
    code = ensure_referral_code(session, client_id=referrer.id)
    for index in range(3):
        referred = _create_client(
            session,
            telegram_id=200 + index,
            display_name=f"Friend {index}",
        )
        register_referral_start(
            session,
            referral_code=code.code,
            referred_client_id=referred.id,
        )
        booking = _create_booking(
            session,
            client=referred,
            starts_at=datetime(2026, 6, 25 + index, 10, 0, tzinfo=UTC),
        )
        complete_booking(
            session,
            booking_id=booking.id,
            final_amount=Decimal("90.00"),
        )
    return referrer


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
    telegram_id: int,
    display_name: str,
) -> Client:
    client = Client(
        user=User(
            telegram_id=telegram_id,
            username=f"user_{telegram_id}",
            display_name=display_name,
        ),
        display_name=display_name,
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


def _create_booking(
    session: Session,
    *,
    client: Client,
    starts_at: datetime,
) -> Booking:
    slot = _create_slot(session, starts_at=starts_at)
    booking = Booking(
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
    session.add(booking)
    session.flush()
    return booking
