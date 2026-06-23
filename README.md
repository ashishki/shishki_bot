# shishki_bot

Standard-mode Python scaffold for a Telegram booking and lightweight operations
bot for one stylist.

## Current Status

- Phase 3 is active. T08 is complete: client start, booking, complex-service
  redirect, and active-booking handler tests are in place.
- Next task: T09 admin manual booking and edits.
- Cycle 4 T07 admin auth review findings were closed before T08.
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

## Repository Layout

- `app/config.py` - environment-backed settings.
- `app/main.py` - import-safe application entrypoint.
- `app/bot/handlers/` - Telegram handler modules for admin and client flows.
- `app/bot/keyboards.py` - reusable bot menu and callback payload definitions.
- `app/db/models.py` - SQLAlchemy models for users, clients, slots, bookings,
  status history, notifications, reminders, and expenses.
- `app/db/session.py` - async engine/session helpers.
- `tests/` - smoke, model, service, notification, and handler tests.

## Workflow

This repository uses Codex for implementation. Claude Code slash commands are
not required. If a playbook instruction mentions `/bootstrap-new`, use
`docs/CODEX_PROMPT.md` and `docs/tasks.md` as the Codex equivalent entrypoint.
