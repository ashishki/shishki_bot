# shishki_bot

Standard-mode Python scaffold for a Telegram booking and lightweight operations
bot for one stylist.

## Current Status

- Phase 5 is complete. T24 is complete: `Рабочее время` is a button-driven
  admin flow with date selection, presets, per-hour actions, and confirmation.
- Next task: none in the current task graph.
- Cycle 9 T13 deployment/operator review findings were closed.
- Production v1 remains deterministic: no production LLM behavior or external
  skills are planned.

## Start Here

- `docs/PROJECT_BRIEF.md` - product brief and constraints.
- `docs/ARCHITECTURE.md` - architecture and mode decision.
- `docs/spec.md` - product behavior and acceptance criteria.
- `docs/tasks.md` - implementation task graph.
- `docs/CODEX_PROMPT.md` - current Codex handoff state.
- `docs/IMPLEMENTATION_CONTRACT.md` - implementation rules.

## Current Verification

```bash
python3 -m venv .venv
. .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -r requirements-dev.txt -e .
python -m ruff check app tests
python -m ruff format --check app tests
python -m pytest tests -q
python3 tools/integrity_check.py --root .
python3 tools/skill_security_gate.py --root . --discover-agent-skills --require-scanner
```

The CI workflow runs the same lint, format, test, integrity, and external skill
security checks on push and pull request.

## Local Setup

```bash
python3 -m venv .venv
. .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -r requirements-dev.txt -e .
```

Runtime configuration is read only from environment variables:

| Variable | Required | Notes |
|----------|----------|-------|
| `BOT_TOKEN` | yes | Telegram bot token. Do not commit it. |
| `ADMIN_TELEGRAM_IDS` | yes | Comma-separated Telegram numeric user IDs allowed to use admin actions. |
| `DATABASE_URL` | yes | Local prototype can use `sqlite+aiosqlite:///./shishki_bot.db`; production should use PostgreSQL. |
| `TIMEZONE` | yes | Business timezone, for example `Asia/Tbilisi`. |
| `DEFAULT_PLACE` | yes | Default appointment address shown to clients. |
| `STYLIST_CONTACT_URL` | yes | Public contact link for complex-service redirects. |
| `DEFAULT_MAP_URL` | no | Optional map link in client-facing messages. |
| `YANDEX_PLACE` / `YANDEX_MAP_URL` | no | Optional Yandex Maps link shown as `Yandex` in address lines. |
| `GOOGLE_PLACE` / `GOOGLE_MAP_URL` | no | Optional Google Maps link shown as `Google` in address lines. |
| `WEBHOOK_SECRET` | no | Reserved for webhook deployment mode. Current runtime uses polling. |
| `ENV` | no | Environment label, defaults to `local`. |

Example local environment:

```bash
export BOT_TOKEN="123456:test-token"
export ADMIN_TELEGRAM_IDS="111111111"
export DATABASE_URL="sqlite+aiosqlite:///./shishki_bot.db"
export TIMEZONE="Asia/Tbilisi"
export DEFAULT_PLACE="Studio address"
export STYLIST_CONTACT_URL="https://t.me/stylist"
export YANDEX_PLACE="https://yandex.example/..."
export GOOGLE_PLACE="https://google.example/..."
```

Before the first local startup, create the database schema:

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

## Bot Startup

After installing dependencies and exporting environment variables:

```bash
shishki-bot
```

Equivalent module command:

```bash
python -m app.main
```

The current runtime starts aiogram polling. Deployment and operator notes live in
`docs/DEPLOYMENT.md` and `docs/ADMIN_GUIDE.md`.

## Repository Layout

- `app/config.py` - environment-backed settings.
- `app/main.py` - import-safe application entrypoint.
- `app/bot/handlers/` - Telegram handler modules for admin and client flows.
- `app/bot/keyboards.py` - reusable bot menu and callback payload definitions.
- `app/db/models.py` - SQLAlchemy models for users, clients, slots, bookings,
  status history, notifications, reminders, expenses, referrals, and bonuses.
- `app/db/session.py` - async engine/session helpers.
- `app/scheduler.py` - reminder recovery, runtime delivery, and referral-bonus
  admin reminder scheduler.
- `app/services/` - booking, notification, reminder, finance, client history,
  and referral services.
- `tests/` - smoke, model, service, notification, and handler tests.

## Workflow

This repository uses Codex for implementation. Claude Code slash commands are
not required. If a playbook instruction mentions `/bootstrap-new`, use
`docs/CODEX_PROMPT.md` and `docs/tasks.md` as the Codex equivalent entrypoint.
