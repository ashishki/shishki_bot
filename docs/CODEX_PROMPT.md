# CODEX_PROMPT.md

Version: 1.1
Date: 2026-06-23
Mode: Standard
Phase: 5

## Current State

- Phase: 5
- Baseline: T16 complete; task graph complete with 75 total tests.
- Ruff: configured in `pyproject.toml` for `app/` and `tests/`.
- CI: installs dev dependencies and runs ruff check, ruff format --check, pytest, integrity check, and skill security gate.
- Last verification: 2026-06-24 - ruff check, ruff format --check, pytest `tests -q` (75 passed), integrity check, and skill security gate passed.
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

none - implementation task graph complete through T16.

For future changes, read:

- `docs/tasks.md`
- `docs/ARCHITECTURE.md`
- `docs/spec.md`
- `docs/IMPLEMENTATION_CONTRACT.md`
- `README.md`
- `docs/ADMIN_GUIDE.md`
- `docs/DEPLOYMENT.md`

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

empty - no P0/P1/P2 findings remain from the T13 targeted review.

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

none - Cycle 1 P2 findings CODE-1 and CODE-2 were addressed during T05.

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
- 2026-06-23 - T05 Booking Service And Slot Locking: added deterministic
  haircut booking creation, slot availability checks, double-booking
  prevention, non-null booking slot invariant, and async session helper tests.
- 2026-06-23 - T06 Message Templates And Notification Service: added reusable
  booking confirmation/change templates and notification delivery logging with
  fake-sender tests for success and failure.
- 2026-06-23 - T07 Admin Authorization And Menus: added allowlisted admin
  command/callback handlers, admin menu actions, callback payload validation,
  and router registration behind `ADMIN_TELEGRAM_IDS`.
- 2026-06-23 - T08 Client Booking Handlers: added client start menu,
  haircut slot selection with explicit confirmation, complex-service redirect,
  active booking lookup, unknown-input fallback, and runtime async DB session
  dispatch coverage.
- 2026-06-23 - T09 Admin Manual Booking And Edits: added admin-created
  complex bookings, reschedule/cancel/detail edit services, status history,
  admin allowlist wrappers, client notification logging, cancelled-slot reuse,
  and collision/error regression coverage.
- 2026-06-23 - T10 Reminder Scheduler: added restart-safe reminder
  reconstruction, scheduler DTOs, atomic reminder delivery claiming,
  duplicate-send prevention, reschedule reconciliation, and recovery tests.
- 2026-06-23 - T11 Completion, Expenses, And Revenue: added booking
  completion, final amount and expense recording, weekly gross/net summaries,
  admin finance wrappers, and financial-calculation regression tests.
- 2026-06-23 - T12 Client History: added client card summaries, completed
  visit history, total-spent/service/last-visit calculations, admin client-card
  wrapper, and client-history regression tests.
- 2026-06-23 - T13 Deployment And Operator Guide: documented local setup,
  environment variables, schema initialization, bot startup, admin operations,
  safe testing, backup, restore, rollback, and deployment notes.
- 2026-06-24 - T14 Referral Tracking And Bonuses: added client personal
  referral links, deep-link source capture, completed-visit qualification,
  admin client-card progress, pending cosmetics/styling bonuses, awarded-state
  handling, and one-time admin bonus reminders.
- 2026-06-24 - T15 Client Service Menu And Booking Guard: changed `/start` to
  show explicit service choices for haircut, coloring, and consultation; kept
  haircut date/slot booking behind the haircut button; routed coloring and
  consultation to stylist chat; and added a 2-active-haircuts-per-day client
  guard.
- 2026-06-24 - T16 Client UX Copy Cleanup: simplified the first screen,
  removed referrals/reschedule/contact from the primary menu, corrected
  referral copy grammar, separated booking confirmation copy from the active
  booking view, and added a `Главное меню` return action.

## Completed Bootstrap Work

- Lean scaffold created.
- Project brief expanded for client UX, admin booking management, reminders,
  manual complex-service bookings, revenue stats, expenses, and client history.
- Repository promoted to Standard mode because the app is customer-facing and
  stores client/booking/finance data.
- Claude Code command flow is not used. Codex is the implementation surface.
- Local Telegram testing setup completed for supplied credentials: Russian
  client/admin UX, 2026-06-27 haircut slots, map-link message templates, client
  self-service booking management, admin client/schedule controls, and a running
  background bot process with PID recorded in `bot.pid`.
- Reminder delivery is wired into runtime: `app.main` starts the reminder
  scheduler with the bot, due reminders are sent through Telegram, and the
  current systemd service has been restarted on the updated code.
- Client menu includes an `О мастере` option that sends `IMG_9385.PNG` with
  the text from `about_me.md` and follow-up buttons for booking/contact.
- Client menu includes `Рекомендации`; personal deep links are recorded through
  `/start ref_<code>`, qualified after completed visits, and every 3 qualified
  referrals creates a pending professional hair cosmetics/styling bonus for
  admin follow-up.
- Client start menu now asks for service selection: `Стрижка` leads to dates
  and slots, while `Окрашивание` and `Консультация` route to stylist chat.
  One Telegram client cannot hold more than 2 active haircut bookings on the
  same date through self-booking.
- Primary client menu is intentionally limited to `Стрижка`, `Окрашивание`,
  `Консультация`, `Моя запись`, and `О мастере`; referral access is shown after
  booking and inside the active booking flow.

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
