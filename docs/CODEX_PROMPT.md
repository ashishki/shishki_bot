# CODEX_PROMPT.md

Version: 1.1
Date: 2026-07-01
Mode: Standard
Phase: 5

## Current State

- Phase: 5
- Baseline: T25 complete; task graph complete with 90 total tests.
- Ruff: configured in `pyproject.toml` for `app/` and `tests/`.
- CI: installs dev dependencies and runs ruff check, ruff format --check, pytest, integrity check, and skill security gate.
- Last verification: 2026-07-01 - ruff check, ruff format --check, pytest `tests -q` (90 passed), integrity check, and skill security gate passed.
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

none - implementation task graph complete through T25.

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
- 2026-06-24 - T17 Client Flow Consistency Cleanup: shortened the `/start`
  greeting to avoid stylist branding, price, and duration on the first screen;
  expanded `О мастере`, coloring, consultation, no-active-booking, cancellation,
  and reschedule follow-ups so service choices and main menu remain reachable.
- 2026-06-24 - T18 Manual Booking And Official Slots: added admin `/book`
  command for manual service bookings, persisted coloring/consultation contact
  clients for admin follow-up, blocked overlapping active bookings from
  self-booking availability, improved stale-slot recovery, cleared test
  booking/slot data after backup, and loaded official 2026-06-28 and 2026-07-04
  haircut slots.
- 2026-06-25 - T19 Admin Booking Event Notifications: wired client
  self-booking, client reschedule, and client cancellation confirmations to
  notify every configured admin after commit and record delivery logs.
- 2026-06-28 - T20 Haircut Variants And Admin Slot Closures: split
  self-booked haircut into male/female variants with 100/120 GEL pricing,
  added admin-visible client identity/chat in booking messages, allowed manual
  booking by client ID or Telegram username, added admin slot/day closing
  commands, and updated the live July schedule after backup.
- 2026-06-28 - T21 Admin Dashboard And Price-Free Reminders: changed
  `/admin` into a live dashboard with upcoming bookings, client counts, free
  slots, weekly metrics, pending bonuses, people metrics, and quick controls;
  reminder messages are covered by tests to avoid showing price.
- 2026-06-30 - T22 Admin Working Time Reopen And Referral Start CTA: added
  admin commands for opening one hour or a whole working day, restored the
  referral bonus CTA to the first client screen, and moved the live local July
  schedule from 2026-07-10 to 2026-07-12 after backup.
- 2026-06-30 - T23 Admin Callback Button Runtime Coverage: extracted admin
  callback dispatch into a testable runtime helper and added regression
  coverage that presses every main dashboard button payload.
- 2026-06-30 - T24 Button-Driven Working Time Admin UX: changed `Рабочее время`
  from command-only help into a date/preset/hour/confirmation button flow while
  keeping `/open`, `/open_day`, `/close`, and `/close_day` as fast shortcuts.
- 2026-07-01 - T25 Local Slot Time Confirmation Fix: fixed booking creation
  and reschedule paths so naive SQLite slot times remain business-local in
  immediate client/admin messages instead of being treated as UTC.

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
  current systemd service has been restarted on the updated code. Reminder
  messages do not include appointment price.
- Client menu includes an `О мастере` option that sends `IMG_9385.PNG` with
  the text from `about_me.md` and follow-up buttons for booking/contact.
- Client menu includes `Рекомендации`; personal deep links are recorded through
  `/start ref_<code>`, qualified after completed visits, and every 3 qualified
  referrals creates a pending professional hair cosmetics/styling bonus for
  admin follow-up.
- Client start menu asks for service selection. `Стрижка` leads to male/female
  haircut choice, then dates and slots; male haircut is 100 GEL and female
  haircut is 120 GEL. `Окрашивание` and `Консультация` route to stylist chat.
  One Telegram client cannot hold more than 2 active haircut bookings on the
  same date through self-booking.
- Primary client menu shows `Стрижка`, `Окрашивание`, `Консультация`,
  `Моя запись`, `Рекомендации`, and `О мастере`; the first greeting does not
  show haircut price/duration and briefly mentions the referral bonus.
- Admin manual bookings can be created with `/book <client_id|@username>
  <YYYY-MM-DD> <HH:MM> <minutes> <price> <service>`. The client must have a
  client card first, usually by pressing `/start`, `Окрашивание`, or
  `Консультация`. Admin schedule and notification views show the client name,
  ID, and chat link when available.
- Admin can create/reopen free time with `/open <YYYY-MM-DD> <HH:MM>` or
  `/open_day <YYYY-MM-DD> <HH:MM> <HH:MM>`, hide one free slot with
  `/close <YYYY-MM-DD> <HH:MM>`, or close the remaining free slots in a day
  with `/close_day <YYYY-MM-DD> <HH:MM>`. The `Рабочее время` admin button now
  provides date selection, presets, per-hour actions, and confirmation before
  applying those same mutations.
- Booking creation and reschedule preserve naive SQLite slot times as local
  business times for stored booking fields and immediate confirmation/change
  messages. UTC conversion is used only for comparisons such as past-slot
  checks.
- `/admin` opens the admin dashboard: upcoming bookings with client links,
  client counts, free slots, weekly revenue, pending bonuses, and quick controls
  for records, clients, metrics, manual booking, working time, today, and
  bonuses. The metrics screen shows weekly revenue/net and top clients by
  completed visits/spend. Dashboard button callbacks are regression-tested
  through the runtime dispatch path used by Telegram.
- Live local database was backed up to
  `/srv/openclaw-you/backups/shishki_bot/shishki_bot_before_official_slots_20260624_130105.db`
  before clearing test booking/slot records. Active official slots are
  2026-06-28 13:00-19:00, 2026-07-04 10:00-15:00 with active bookings at
  14:00 and 15:00 and closed slots from 16:00, 2026-07-08 10:00-19:00,
  and 2026-07-12 10:00-19:00 at the configured address. 2026-07-10 is closed.
- Latest live database backup before T22 schedule edits:
  `/srv/openclaw-you/backups/shishki_bot/shishki_bot_before_t22_schedule_20260630_170754.db`.

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
