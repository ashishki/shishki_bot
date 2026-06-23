# CODEX_PROMPT.md

Version: 1.1
Date: 2026-06-23
Mode: Standard
Phase: 2

## Current State

- Phase: 2
- Baseline: Phase 1 complete through T04; Cycle 1 review complete with no P0/P1 findings and 2 open P2 findings. T05 is the next implementation task.
- Ruff: configured in `pyproject.toml` for `app/` and `tests/`.
- CI: installs dev dependencies and runs ruff check, ruff format --check, pytest, integrity check, and skill security gate.
- Last verification: 2026-06-23 - ruff check, ruff format --check, pytest `tests -q` (5 passed), integrity check, and skill security gate passed. Cycle 1 audit reran `python3 tools/integrity_check.py --root .` successfully; direct pytest rerun was unavailable from `/usr/bin/python3` because pytest is not installed there.
- AI/model budget: not applicable for production v1; development model use is governed by `docs/COST_BUDGET.md`.
- Production AI usage: none.
- External skills: not applicable; none planned or installed.

## Continuity Pointers

- Project brief: `docs/PROJECT_BRIEF.md`
- Architecture: `docs/ARCHITECTURE.md`
- Product spec: `docs/spec.md`
- Task graph: `docs/tasks.md`
- Implementation contract: `docs/IMPLEMENTATION_CONTRACT.md`
- Decision log: `docs/DECISION_LOG.md`
- Implementation journal: `docs/IMPLEMENTATION_JOURNAL.md`
- Evidence index: `docs/EVIDENCE_INDEX.md`

## Next Task

T05: Booking Service And Slot Locking

Before editing, read:

- `docs/tasks.md#t05-booking-service-and-slot-locking`
- `docs/IMPLEMENTATION_CONTRACT.md`
- `docs/spec.md#feature-2---simple-haircut-booking`

## Verification

Current local verification:

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

## Fix Queue

empty - no P0/P1 blockers from Cycle 1; proceed to the phase queue.

## Capability State

### RAG State

- Status: OFF
- Active corpora: n/a
- Retrieval baseline: n/a
- Open retrieval findings: none

### Tool-Use State

- Status: OFF
- Tool catalog: n/a
- Unsafe tools: none
- Open tool findings: none

### Agentic State

- Status: OFF
- Active loops: none
- Termination contract: n/a
- Open agent findings: none

### Planning State

- Status: OFF
- Plan schema: n/a
- Open planning findings: none

### Compliance State

- Status: OFF
- Named framework: n/a
- Control baseline: n/a
- Open compliance findings: none

## Open Findings

| ID | Sev | Description | Status | Next |
|----|-----|-------------|--------|------|
| CODE-1 | P2 | `Booking.slot_id` is nullable even though booking creation/reschedule must target and lock a slot. | Open | Make `slot_id` non-null and add an integrity regression test when hardening T05/T04 persistence. |
| CODE-2 | P2 | Async session helpers lack tests for engine creation, session factory, create/drop helpers, and `session_scope` commit/rollback. | Open | Add async persistence tests using `sqlite+aiosqlite:///:memory:` before relying on these helpers in booking service work. |

## Completed Tasks

- 2026-06-23 - T01 Project Skeleton: added package metadata, runtime/dev
  requirements, `app/config.py`, side-effect-free `app/main.py`, and smoke
  tests for settings and imports.
- 2026-06-23 - T02 CI And Local Verification: activated GitHub Actions
  verification and documented the full local command in README and this handoff.
- 2026-06-23 - T03 First Smoke Tests: strengthened settings and import smoke
  tests so supplied test settings do not read real environment values and
  importing `app.main` does not import `aiogram`.
- 2026-06-23 - T04 Database Models And Migrations: added SQLAlchemy models for
  users, clients, slots, bookings, status history, notification logs, reminder
  logs, and booking expenses, plus metadata create/drop tests.

## Completed Bootstrap Work

- Lean scaffold created.
- Project brief expanded for client UX, admin booking management, reminders,
  manual complex-service bookings, revenue stats, expenses, and client history.
- Repository promoted to Standard mode because the app is customer-facing and
  stores client/booking/finance data.
- Claude Code command flow is not used. Codex is the implementation surface.

## Instructions For Codex

1. Start from the current task in `docs/tasks.md`.
2. Keep changes inside the task file scope unless verification proves more
   context is required.
3. Do not use `.claude` settings or commands as required workflow.
4. Add or update tests for behavior changes.
5. Run the task verification before completion.
6. Update this file, `docs/IMPLEMENTATION_JOURNAL.md`, and `docs/EVIDENCE_INDEX.md`
   at meaningful phase or evidence boundaries.
7. Stop for approval before adding payments, external integrations, production
   AI behavior, new admin users, or data migrations affecting real data.
