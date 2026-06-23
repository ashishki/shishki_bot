# shishki_bot

Standard-mode Python scaffold for a Telegram booking and lightweight operations
bot for one stylist.

## Current Status

- Phase 5 is active. T12 is complete: client card, visit history, and
  completed-booking total-spent tests are in place.
- Next task: T13 deployment and operator guide.
- Cycle 8 T12 client-history review findings were closed before T13.
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
- `app/scheduler.py` - reminder recovery job DTO adapter.
- `app/services/` - booking, notification, reminder, finance, and client history
  services.
- `tests/` - smoke, model, service, notification, and handler tests.

## Workflow

This repository uses Codex for implementation. Claude Code slash commands are
not required. If a playbook instruction mentions `/bootstrap-new`, use
`docs/CODEX_PROMPT.md` and `docs/tasks.md` as the Codex equivalent entrypoint.
