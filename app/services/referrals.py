"""Referral tracking and bonus eligibility rules."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
from html import escape
from secrets import token_urlsafe

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.db.models import (
    Booking,
    BookingStatus,
    Client,
    Referral,
    ReferralBonus,
    ReferralBonusStatus,
    ReferralCode,
    ReferralManualCredit,
    ReferralStatus,
)

REFERRAL_START_PREFIX = "ref_"
REFERRAL_REWARD_LABEL = (
    "классная профессиональная косметика для волос: уход или стайлинг"
)
REFERRAL_BONUS_THRESHOLD = 3


class ReferralServiceError(ValueError):
    """Raised when deterministic referral rules reject a request."""


@dataclass(frozen=True, slots=True)
class ReferralRegistrationResult:
    referral: Referral | None
    registered: bool
    reason: str | None = None


@dataclass(frozen=True, slots=True)
class ReferralProgress:
    code: str | None
    qualified_count: int
    manual_credit_count: int
    credited_count: int
    pending_count: int
    pending_bonus_count: int
    awarded_bonus_count: int
    next_bonus_remaining: int


@dataclass(frozen=True, slots=True)
class ReferralManualCreditResult:
    credit: ReferralManualCredit
    created: bool
    bonuses: tuple[ReferralBonus, ...]


def ensure_referral_code(session: Session, *, client_id: int) -> ReferralCode:
    client = session.get(Client, client_id)
    if client is None:
        raise ReferralServiceError(f"Client not found: {client_id}")

    existing = session.scalar(
        select(ReferralCode).where(ReferralCode.client_id == client_id)
    )
    if existing is not None:
        return existing

    for _attempt in range(3):
        code = ReferralCode(client_id=client_id, code=token_urlsafe(8))
        try:
            with session.begin_nested():
                session.add(code)
                session.flush()
        except IntegrityError:
            continue
        return code

    raise ReferralServiceError("Could not allocate a unique referral code")


def build_referral_link(*, bot_username: str, code: str) -> str:
    username = bot_username.strip().lstrip("@")
    if not username:
        raise ReferralServiceError("bot_username is required")
    return f"https://t.me/{username}?start={REFERRAL_START_PREFIX}{code}"


def referral_code_from_start_payload(start_payload: str | None) -> str | None:
    if not start_payload:
        return None
    payload = start_payload.strip()
    if not payload.startswith(REFERRAL_START_PREFIX):
        return None
    code = payload.removeprefix(REFERRAL_START_PREFIX).strip()
    return code or None


def register_referral_start(
    session: Session,
    *,
    referral_code: str | None,
    referred_client_id: int,
) -> ReferralRegistrationResult:
    if not referral_code:
        return ReferralRegistrationResult(
            referral=None,
            registered=False,
            reason="missing referral code",
        )

    code = session.scalar(
        select(ReferralCode).where(ReferralCode.code == referral_code)
    )
    if code is None:
        return ReferralRegistrationResult(
            referral=None,
            registered=False,
            reason="unknown referral code",
        )

    if code.client_id == referred_client_id:
        return ReferralRegistrationResult(
            referral=None,
            registered=False,
            reason="self referral ignored",
        )

    existing = session.scalar(
        select(Referral).where(Referral.referred_client_id == referred_client_id)
    )
    if existing is not None:
        return ReferralRegistrationResult(
            referral=existing,
            registered=False,
            reason="referral already recorded",
        )

    if _client_has_bookings(session, client_id=referred_client_id):
        return ReferralRegistrationResult(
            referral=None,
            registered=False,
            reason="existing client ignored",
        )

    referral = Referral(
        referrer_client_id=code.client_id,
        referred_client_id=referred_client_id,
        referral_code_id=code.id,
        status=ReferralStatus.PENDING,
    )
    try:
        with session.begin_nested():
            session.add(referral)
            session.flush()
    except IntegrityError:
        existing = session.scalar(
            select(Referral).where(Referral.referred_client_id == referred_client_id)
        )
        if existing is None:
            raise
        return ReferralRegistrationResult(
            referral=existing,
            registered=False,
            reason="referral already recorded",
        )

    return ReferralRegistrationResult(referral=referral, registered=True)


def qualify_referral_for_booking(
    session: Session,
    *,
    booking: Booking,
) -> tuple[ReferralBonus, ...]:
    if booking.status is not BookingStatus.COMPLETED:
        return ()

    referral = session.scalar(
        select(Referral).where(Referral.referred_client_id == booking.client_id)
    )
    if referral is None:
        return ()
    if referral.status is ReferralStatus.QUALIFIED:
        return ()

    now = datetime.now(UTC)
    referral.status = ReferralStatus.QUALIFIED
    referral.qualified_booking_id = booking.id
    referral.qualified_at = now
    session.flush()

    return _ensure_earned_bonuses(session, client_id=referral.referrer_client_id)


def grant_manual_referral_credit(
    session: Session,
    *,
    client_id: int,
    reason: str,
    amount: int = 1,
    dedupe_key: str | None = None,
    created_by: str | None = None,
) -> ReferralManualCreditResult:
    if amount <= 0:
        raise ReferralServiceError("Manual referral credit amount must be positive")
    if not reason.strip():
        raise ReferralServiceError("Manual referral credit reason is required")

    client = session.get(Client, client_id)
    if client is None:
        raise ReferralServiceError(f"Client not found: {client_id}")

    if dedupe_key:
        existing = session.scalar(
            select(ReferralManualCredit).where(
                ReferralManualCredit.dedupe_key == dedupe_key
            )
        )
        if existing is not None:
            if existing.client_id != client_id:
                raise ReferralServiceError(
                    "Manual referral credit key belongs to another client"
                )
            bonuses = _ensure_earned_bonuses(session, client_id=client_id)
            return ReferralManualCreditResult(
                credit=existing,
                created=False,
                bonuses=bonuses,
            )

    credit = ReferralManualCredit(
        client_id=client_id,
        amount=amount,
        reason=reason.strip(),
        dedupe_key=dedupe_key.strip() if dedupe_key else None,
        created_by=created_by.strip() if created_by else None,
    )
    try:
        with session.begin_nested():
            session.add(credit)
            session.flush()
    except IntegrityError as exc:
        if not dedupe_key:
            raise
        existing = session.scalar(
            select(ReferralManualCredit).where(
                ReferralManualCredit.dedupe_key == dedupe_key
            )
        )
        if existing is None:
            raise
        if existing.client_id != client_id:
            raise ReferralServiceError(
                "Manual referral credit key belongs to another client"
            ) from exc
        bonuses = _ensure_earned_bonuses(session, client_id=client_id)
        return ReferralManualCreditResult(
            credit=existing,
            created=False,
            bonuses=bonuses,
        )

    bonuses = _ensure_earned_bonuses(session, client_id=client_id)
    return ReferralManualCreditResult(credit=credit, created=True, bonuses=bonuses)


def referral_progress(session: Session, *, client_id: int) -> ReferralProgress:
    qualified_count = _qualified_referral_count(session, client_id=client_id)
    manual_credit_count = _manual_referral_credit_count(session, client_id=client_id)
    credited_count = qualified_count + manual_credit_count
    pending_count = len(
        tuple(
            session.scalars(
                select(Referral).where(
                    Referral.referrer_client_id == client_id,
                    Referral.status == ReferralStatus.PENDING,
                )
            )
        )
    )
    pending_bonus_count = len(
        tuple(
            session.scalars(
                select(ReferralBonus).where(
                    ReferralBonus.client_id == client_id,
                    ReferralBonus.status == ReferralBonusStatus.PENDING,
                )
            )
        )
    )
    awarded_bonus_count = len(
        tuple(
            session.scalars(
                select(ReferralBonus).where(
                    ReferralBonus.client_id == client_id,
                    ReferralBonus.status == ReferralBonusStatus.AWARDED,
                )
            )
        )
    )
    code = session.scalar(
        select(ReferralCode).where(ReferralCode.client_id == client_id)
    )
    next_bonus_remaining = REFERRAL_BONUS_THRESHOLD - (
        credited_count % REFERRAL_BONUS_THRESHOLD
    )
    if next_bonus_remaining == REFERRAL_BONUS_THRESHOLD and credited_count:
        next_bonus_remaining = REFERRAL_BONUS_THRESHOLD

    return ReferralProgress(
        code=code.code if code else None,
        qualified_count=qualified_count,
        manual_credit_count=manual_credit_count,
        credited_count=credited_count,
        pending_count=pending_count,
        pending_bonus_count=pending_bonus_count,
        awarded_bonus_count=awarded_bonus_count,
        next_bonus_remaining=next_bonus_remaining,
    )


def pending_referral_bonuses(session: Session) -> tuple[ReferralBonus, ...]:
    return tuple(
        session.scalars(
            select(ReferralBonus)
            .where(ReferralBonus.status == ReferralBonusStatus.PENDING)
            .order_by(ReferralBonus.created_at, ReferralBonus.id)
        )
    )


def pending_referral_bonus_notifications(session: Session) -> tuple[ReferralBonus, ...]:
    return tuple(
        session.scalars(
            select(ReferralBonus)
            .where(
                ReferralBonus.status == ReferralBonusStatus.PENDING,
                ReferralBonus.notification_sent_at.is_(None),
            )
            .order_by(ReferralBonus.created_at, ReferralBonus.id)
        )
    )


def mark_referral_bonus_notified(
    session: Session,
    *,
    bonus_id: int,
    notified_at: datetime | None = None,
) -> ReferralBonus:
    bonus = _get_bonus(session, bonus_id=bonus_id)
    bonus.notification_sent_at = notified_at or datetime.now(UTC)
    session.flush()
    return bonus


def mark_referral_bonus_awarded(
    session: Session,
    *,
    bonus_id: int,
    awarded_at: datetime | None = None,
) -> ReferralBonus:
    bonus = _get_bonus(session, bonus_id=bonus_id)
    bonus.status = ReferralBonusStatus.AWARDED
    bonus.awarded_at = awarded_at or datetime.now(UTC)
    session.flush()
    return bonus


def referral_bonus_admin_message(bonus: ReferralBonus) -> str:
    return "\n".join(
        [
            "Бонус за рекомендации",
            "",
            f"Клиент: {_html(_display_name(bonus.client))} #{bonus.client_id}",
            f"Засчитано к бонусу: {bonus.referral_count}",
            f"Подарок: {bonus.reward_label}",
            "",
            "Откройте /admin -> Бонусы, чтобы отметить выдачу.",
        ]
    )


def _ensure_earned_bonuses(
    session: Session,
    *,
    client_id: int,
) -> tuple[ReferralBonus, ...]:
    credited_count = _credited_referral_count(session, client_id=client_id)
    earned_counts = range(
        REFERRAL_BONUS_THRESHOLD,
        credited_count + 1,
        REFERRAL_BONUS_THRESHOLD,
    )
    created: list[ReferralBonus] = []
    for referral_count in earned_counts:
        existing = session.scalar(
            select(ReferralBonus).where(
                ReferralBonus.client_id == client_id,
                ReferralBonus.referral_count == referral_count,
            )
        )
        if existing is not None:
            continue
        bonus = ReferralBonus(
            client_id=client_id,
            referral_count=referral_count,
            reward_label=REFERRAL_REWARD_LABEL,
            status=ReferralBonusStatus.PENDING,
        )
        session.add(bonus)
        created.append(bonus)
    session.flush()
    return tuple(created)


def _qualified_referral_count(session: Session, *, client_id: int) -> int:
    return len(
        tuple(
            session.scalars(
                select(Referral).where(
                    Referral.referrer_client_id == client_id,
                    Referral.status == ReferralStatus.QUALIFIED,
                )
            )
        )
    )


def _manual_referral_credit_count(session: Session, *, client_id: int) -> int:
    return sum(
        credit.amount
        for credit in session.scalars(
            select(ReferralManualCredit).where(
                ReferralManualCredit.client_id == client_id
            )
        )
    )


def _credited_referral_count(session: Session, *, client_id: int) -> int:
    return _qualified_referral_count(
        session,
        client_id=client_id,
    ) + _manual_referral_credit_count(session, client_id=client_id)


def _client_has_bookings(session: Session, *, client_id: int) -> bool:
    return (
        session.scalar(select(Booking.id).where(Booking.client_id == client_id))
        is not None
    )


def _get_bonus(session: Session, *, bonus_id: int) -> ReferralBonus:
    bonus = session.get(ReferralBonus, bonus_id)
    if bonus is None:
        raise ReferralServiceError(f"Referral bonus not found: {bonus_id}")
    return bonus


def _display_name(client: Client) -> str:
    if client.display_name:
        return client.display_name
    if client.user and client.user.display_name:
        return client.user.display_name
    if client.user and client.user.username:
        return f"@{client.user.username}"
    return "Клиент"


def _html(value: object) -> str:
    return escape(str(value), quote=False)
