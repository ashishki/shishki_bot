# Deployment Guide

Version: 1.0
Last updated: 2026-06-23

`shishki_bot` is a small deterministic Python 3.12 Telegram bot. The current
runtime uses aiogram polling and environment-backed configuration.

## Target Runtime

- Python 3.12
- Long-running process: `shishki-bot`
- Production database: PostgreSQL
- Local prototype database: SQLite
- Network egress: Telegram Bot API only

No payments, external calendar sync, production AI behavior, or runtime
toolchain mutation are part of v1.

## Required Environment

| Variable | Required | Example |
|----------|----------|---------|
| `BOT_TOKEN` | yes | `123456:abc` |
| `ADMIN_TELEGRAM_IDS` | yes | `111,222` |
| `DATABASE_URL` | yes | `postgresql+asyncpg://user:pass@host/db` |
| `TIMEZONE` | yes | `Asia/Tbilisi` |
| `DEFAULT_PLACE` | yes | `Studio address` |
| `STYLIST_CONTACT_URL` | yes | `https://t.me/stylist` |
| `DEFAULT_MAP_URL` | no | `https://maps.example/...` |
| `YANDEX_PLACE` / `YANDEX_MAP_URL` | no | `https://yandex.example/...` |
| `GOOGLE_PLACE` / `GOOGLE_MAP_URL` | no | `https://google.example/...` |
| `WEBHOOK_SECRET` | no | reserved for future webhook mode |
| `ENV` | no | `production` |

Secrets must come from the deployment platform secret manager or environment,
never from repository files.

Database backup tools use a separate libpq-compatible URL. Keep it in the same
secret manager when needed:

| Variable | Required | Example |
|----------|----------|---------|
| `DATABASE_BACKUP_URL` | backup jobs only | `postgresql://user:pass@host/db` |

Do not pass the application async SQLAlchemy URL
`postgresql+asyncpg://user:pass@host/db` directly to `pg_dump` or `psql`.

## Local Run

```bash
python3 -m venv .venv
. .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -r requirements-dev.txt -e .
export BOT_TOKEN="123456:test-token"
export ADMIN_TELEGRAM_IDS="111111111"
export DATABASE_URL="sqlite+aiosqlite:///./shishki_bot.db"
export TIMEZONE="Asia/Tbilisi"
export DEFAULT_PLACE="Studio address"
export STYLIST_CONTACT_URL="https://t.me/stylist"
export YANDEX_PLACE="https://yandex.example/..."
export GOOGLE_PLACE="https://google.example/..."
python - <<'PY'
import asyncio

from app.db.session import create_all, create_database_engine


async def main() -> None:
    engine = create_database_engine()
    try:
        await create_all(engine)
    finally:
        await engine.dispose()


asyncio.run(main())
PY
shishki-bot
```

## Production Deploy

Use a small VPS or managed container service such as Render, Railway, Fly.io, or
similar.

1. Provision PostgreSQL and enable automatic backups.
2. Configure the required environment variables in the platform secret manager.
3. Install dependencies with `pip install -r requirements.txt -e .`.
4. Run the full verification command from `README.md` before promoting a commit.
5. For a fresh database, initialize the schema with the `create_all` command
   shown below.
6. Start one bot process with `shishki-bot`.
7. Confirm `/admin` is denied for non-admin IDs and works for allowlisted admin
   IDs.

The repository does not require a Dockerfile for v1. This document is the
selected deployment note for T13.

## Verification Before Release

```bash
python -m ruff check app tests
python -m ruff format --check app tests
python -m pytest tests -q
python3 tools/integrity_check.py --root .
python3 tools/skill_security_gate.py --root . --discover-agent-skills --require-scanner
```

Do not deploy a commit that fails any verification step.

## Schema Initialization

For a fresh local or production database, create the schema before first
startup:

```bash
python - <<'PY'
import asyncio

from app.db.session import create_all, create_database_engine


async def main() -> None:
    engine = create_database_engine()
    try:
        await create_all(engine)
    finally:
        await engine.dispose()


asyncio.run(main())
PY
```

This is a non-destructive table creation helper for the current v1 schema. Any
future production data migration must have an explicit task, backup note, and
rollback note before it is run.

For T14 referral tracking, the schema change is additive: `referral_codes`,
`referrals`, and `referral_bonuses` are new tables. On an existing database,
make a fresh backup first, then run the same `create_all` helper to create only
missing tables. Rollback is application rollback plus dropping these new tables
only if the operator explicitly decides referral data created after the rollout
can be discarded.

For T27 manual referral credits, the schema change is additive:
`referral_manual_credits` is a new table. On an existing database, make a fresh
backup first, then run the same `create_all` helper to create only the missing
table. Rollback is application rollback plus dropping `referral_manual_credits`
only if the operator explicitly decides manual bonus-credit history can be
discarded.

## Backup Plan

Production must have a backup path before real client use.

Recommended minimum:

- Enable provider-managed daily PostgreSQL backups.
- Keep at least 7 daily restore points.
- Before risky admin maintenance or any future migration, create an immediate
  manual backup.

Manual backup command shape:

```bash
export DATABASE_BACKUP_URL="postgresql://user:pass@host/db"
pg_dump "$DATABASE_BACKUP_URL" > "backups/shishki_bot_$(date +%Y%m%d_%H%M%S).sql"
```

Manual restore command shape:

```bash
psql "$DATABASE_BACKUP_URL" < backups/shishki_bot_YYYYMMDD_HHMMSS.sql
```

Always make a fresh backup before restoring an older one.

## Rollback Plan

Application rollback:

1. Stop the current bot process.
2. Deploy the previous known-good commit or image.
3. Run the verification command.
4. Start `shishki-bot`.
5. Smoke check `/admin` access and a synthetic local booking flow.

Database rollback:

1. Stop the bot.
2. Save a fresh backup of the current database.
3. Restore the selected verified backup.
4. Start the previous known-good application version.
5. Check booking, reminder, finance, and client-history screens with synthetic
   or admin-owned test data only.

## Safe Testing Rule

Do not run automated tests against real Telegram chats or real clients. Tests
must use fake senders and synthetic local database records.

## Operational Notes

- Bot restart should not lose bookings or pending reminder state because the
  database is canonical and reminders are reconstructed from booking/reminder
  records.
- Notification attempts are logged as sent or failed.
- Client PII-like fields and finance data must not be printed in production logs
  except as redacted/internal IDs.
