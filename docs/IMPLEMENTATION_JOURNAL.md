# Implementation Journal - shishki_bot

Version: 1.0
Last updated: 2026-06-30
Status: append-only

## Entry Template

```markdown
### YYYY-MM-DD - TNN - Short title

- Scope:
- Why:
- Decisions applied:
- Evidence collected:
- Follow-ups:
- Notes:
```

## Entries

### 2026-06-23 - Bootstrap - Lean scaffold

- Scope: `AGENTS.md`, `README.md`, `docs/`, `tools/`, `schemas/`, `.gitignore`
- Why: Initialize repository with the Lean playbook scaffold and project brief.
- Decisions applied: none yet.
- Evidence collected: `python3 tools/integrity_check.py --root .`; `python3 tools/skill_security_gate.py --root . --discover-agent-skills --require-scanner`
- Follow-ups: Fill and refine `docs/PROJECT_BRIEF.md`.
- Notes: Initial repo had no commits and no application code.

### 2026-06-23 - Bootstrap - Promote to Standard

- Scope: `PLAYBOOK.md`, `.github/workflows/ci.yml`, `hooks/`, `docs/ARCHITECTURE.md`, `docs/spec.md`, `docs/tasks.md`, `docs/CODEX_PROMPT.md`, `docs/IMPLEMENTATION_CONTRACT.md`, `docs/DECISION_LOG.md`, `docs/EVIDENCE_INDEX.md`
- Why: `docs/PROJECT_BRIEF.md` expanded from a simple booking bot into a customer-facing booking, notification, admin management, revenue, expense, and client-history system.
- Decisions applied: `D-001`, `D-002`, `D-003`, `D-004`
- Evidence collected: `python3 tools/integrity_check.py --root .`; `python3 tools/skill_security_gate.py --root . --discover-agent-skills --require-scanner`
- Follow-ups: Start T01 Project Skeleton.
- Notes: Claude Code command flow was intentionally not installed; Codex will execute the project tasks.

### 2026-06-23 - PHASE1 - Validate Standard Bootstrap

- Scope: `docs/audit/PHASE1_AUDIT.md`, `docs/audit/AUDIT_INDEX.md`, Phase 1 canonical docs.
- Why: Validate Phase 1 before implementation begins.
- Decisions applied: `D-001`, `D-002`, `D-003`, `D-004`
- Evidence collected: `docs/audit/PHASE1_AUDIT.md`
- Follow-ups: Start T01 Project Skeleton.
- Notes: Result PASS; no blockers.

### 2026-06-23 - T01 - Project Skeleton

- Scope: `pyproject.toml`, `requirements.txt`, `requirements-dev.txt`, `app/`, `tests/`, `docs/CODEX_PROMPT.md`, `docs/tasks.md`, `docs/EVIDENCE_INDEX.md`
- Why: Establish the Python package skeleton, dependency manifests, settings loader, import-safe bot entrypoint, and initial smoke tests.
- Decisions applied: `D-001`, `D-002`, `D-003`, `D-004`
- Evidence collected: ruff check; ruff format --check; pytest smoke tests; `python3 tools/integrity_check.py --root .`; `python3 tools/skill_security_gate.py --root . --discover-agent-skills --require-scanner`
- Follow-ups: T02 must finalize CI and README local verification instructions.
- Notes: Verification used a temporary virtualenv at `/tmp/shishki_bot_venv`.

### 2026-06-23 - T02 - CI And Local Verification

- Scope: `.github/workflows/ci.yml`, `README.md`, `docs/CODEX_PROMPT.md`, `docs/tasks.md`, `docs/EVIDENCE_INDEX.md`
- Why: Make the Python verification workflow active and document the exact local command.
- Decisions applied: `D-001`, `D-002`, `D-003`
- Evidence collected: ruff check; ruff format --check; pytest; `python3 tools/integrity_check.py --root .`; `python3 tools/skill_security_gate.py --root . --discover-agent-skills --require-scanner`
- Follow-ups: T03 should keep the smoke-test baseline explicit and import-safe.
- Notes: GitHub Actions now installs `requirements-dev.txt` and runs the same verification gates.

### 2026-06-23 - T03 - First Smoke Tests

- Scope: `tests/test_config.py`, `tests/test_imports.py`, `docs/CODEX_PROMPT.md`, `docs/tasks.md`, `docs/EVIDENCE_INDEX.md`
- Why: Pin the early no-secret/no-network import baseline before database and handler work begins.
- Decisions applied: `D-002`, `D-003`
- Evidence collected: ruff check; ruff format --check; pytest; integrity check; skill security gate.
- Follow-ups: T04 can add database models and persistence tests on top of the smoke baseline.
- Notes: Import smoke test fails if `app.main` imports `aiogram` during module import.

### 2026-06-23 - T04 - Database Models And Migrations

- Scope: `app/db/models.py`, `app/db/session.py`, `tests/test_models.py`, `docs/CODEX_PROMPT.md`, `docs/tasks.md`, `docs/EVIDENCE_INDEX.md`
- Why: Add the durable data model baseline for bookings, slots, notifications, reminders, expenses, and status history.
- Decisions applied: `D-002`, `D-004`
- Evidence collected: `tests/test_models.py` passed; full pytest passed; ruff check; ruff format --check; integrity check; skill security gate.
- Follow-ups: T05 should build booking creation and slot locking on these models.
- Notes: `app/db/__init__.py` was added as package glue for the new database module.

### 2026-06-23 - Phase 1 - Review And Archive

- Scope: `docs/audit/STRATEGY_NOTE.md`, `docs/audit/META_ANALYSIS.md`, `docs/audit/ARCH_REPORT.md`, `docs/audit/REVIEW_REPORT.md`, `docs/archive/PHASE1_REVIEW.md`, `docs/audit/PHASE_REPORT_LATEST.md`, README indexes, `docs/CODEX_PROMPT.md`
- Why: Close the Phase 1 boundary before Phase 2 booking work starts.
- Decisions applied: `D-001`, `D-002`, `D-003`, `D-004`
- Evidence collected: Cycle 1 review report; phase archive; integrity check.
- Follow-ups: T05 should address or account for P2 findings CODE-1 and CODE-2 while implementing slot locking.
- Notes: Stop-Ship: No. P0: 0, P1: 0, P2: 2.

### 2026-06-23 - T05 - Booking Service And Slot Locking

- Scope: `app/services/booking.py`, `tests/test_booking_service.py`, `app/db/models.py`, `tests/test_models.py`, `docs/CODEX_PROMPT.md`, `docs/tasks.md`, `docs/EVIDENCE_INDEX.md`
- Why: Implement deterministic simple haircut booking and prevent double-booking.
- Decisions applied: `D-002`, `D-004`
- Evidence collected: booking service tests passed; model/session hardening tests passed; full pytest passed; ruff check; ruff format --check; integrity check; skill security gate.
- Follow-ups: T06 must add notification templates and delivery logging.
- Notes: Cycle 1 P2 findings CODE-1 and CODE-2 were addressed by making `Booking.slot_id` non-null and adding async session helper tests.

### 2026-06-23 - Cycle 2 - Targeted T05 Review

- Scope: `docs/audit/META_ANALYSIS.md`, `docs/audit/ARCH_REPORT.md`, `docs/audit/REVIEW_REPORT.md`, `docs/archive/CYCLE2_T05_REVIEW.md`, T05 booking service files.
- Why: Booking transaction/slot locking touches a deep-review escalation boundary.
- Decisions applied: `D-002`, `D-004`
- Evidence collected: Cycle 2 targeted review report; ruff check; ruff format --check; full pytest; integrity check; skill security gate.
- Follow-ups: Proceed to T06 message templates and notification service.
- Notes: Stop-Ship: No. P0: 0, P1: 0, P2: 0.

### 2026-06-23 - T06 - Message Templates And Notification Service

- Scope: `app/bot/messages.py`, `app/services/notifications.py`, `tests/test_notifications.py`, `docs/CODEX_PROMPT.md`, `docs/tasks.md`, `docs/EVIDENCE_INDEX.md`
- Why: Add deterministic notification copy and durable success/failure delivery logs.
- Decisions applied: `D-002`
- Evidence collected: notification tests passed; full pytest passed; ruff check; ruff format --check; integrity check; skill security gate.
- Follow-ups: T07 must add admin allowlist checks and menus.
- Notes: Tests use a fake sender and do not send Telegram messages.

### 2026-06-23 - Cycle 3 - Targeted T06 Review

- Scope: `docs/audit/META_ANALYSIS.md`, `docs/audit/ARCH_REPORT.md`, `docs/audit/REVIEW_REPORT.md`, `docs/archive/CYCLE3_T06_REVIEW.md`, T06 notification files.
- Why: Notification delivery semantics touch a deep-review escalation boundary.
- Decisions applied: `D-002`
- Evidence collected: Cycle 3 targeted review report; ruff check; ruff format --check; full pytest; integrity check; skill security gate.
- Follow-ups: Proceed to T07 admin authorization and menus.
- Notes: Stop-Ship: No. P0: 0, P1: 0, P2: 0.

### 2026-06-23 - T07 - Admin Authorization And Menus

- Scope: `app/bot/handlers/admin.py`, `app/bot/keyboards.py`, `app/main.py`, `tests/test_admin_auth.py`, `docs/CODEX_PROMPT.md`, `docs/tasks.md`, `docs/EVIDENCE_INDEX.md`
- Why: Add the admin authorization boundary and menu actions before client booking handlers start wiring bot flows.
- Decisions applied: `D-002`, `D-003`
- Evidence collected: admin auth tests passed; full pytest passed; ruff check; ruff format --check; integrity check; skill security gate.
- Follow-ups: T08 should reuse `app/bot/keyboards.py` patterns for client menu actions and keep handler imports side-effect-free.
- Notes: `app/main.py` now registers the admin router at runtime while keeping `aiogram` imports deferred.

### 2026-06-23 - Cycle 4 - Targeted T07 Review

- Scope: `docs/archive/CYCLE4_T07_REVIEW.md`, T07 admin auth and menu files.
- Why: Admin authorization is a contract security boundary and required targeted review after implementation.
- Decisions applied: `D-002`, `D-003`
- Evidence collected: initial targeted review findings; handler-boundary fixes; repeat review with no P0/P1/P2 findings; full verification.
- Follow-ups: Proceed to T08 client booking handlers.
- Notes: Stop-Ship: No. P0: 0, P1: 0, P2: 0.

### 2026-06-23 - T08 - Client Booking Handlers

- Scope: `app/bot/handlers/client.py`, `app/bot/keyboards.py`, `app/config.py`, `app/main.py`, `tests/test_client_handlers.py`, `tests/test_config.py`, `docs/CODEX_PROMPT.md`, `docs/tasks.md`, `docs/EVIDENCE_INDEX.md`
- Why: Add the client Telegram flow for start menu, haircut booking, complex-service redirect, active booking lookup, and reschedule/cancel contact path.
- Decisions applied: `D-002`, `D-003`, `D-004`
- Evidence collected: client handler tests passed; async callback dispatch coverage passed; full pytest passed; ruff check; ruff format --check; integrity check; skill security gate.
- Follow-ups: T09 should build admin-created complex bookings and admin edits on the same booking/notification service boundaries.
- Notes: Targeted light review found runtime session wiring and confirmation-step gaps; both were fixed before completion. Final verification passed with 30 tests.

### 2026-06-23 - T09 - Admin Manual Booking And Edits

- Scope: `app/db/models.py`, `app/services/booking.py`, `app/bot/messages.py`, `app/bot/handlers/admin.py`, `tests/test_admin_booking.py`, `docs/CODEX_PROMPT.md`, `docs/tasks.md`, `docs/EVIDENCE_INDEX.md`
- Why: Add admin-created complex bookings plus admin reschedule, cancel, and detail-edit behavior with audit history and client notification integrity.
- Decisions applied: `D-002`, `D-003`, `D-004`
- Evidence collected: admin booking tests passed; booking/model regression tests passed; full pytest passed; ruff check; ruff format --check; integrity check; skill security gate.
- Follow-ups: T10 should build reminders using the notification log and status model already established.
- Notes: Targeted review found edit-notification and cancelled-slot reuse issues; both were fixed before completion. Final verification passed with 36 tests.

### 2026-06-23 - Cycle 5 - Targeted T09 Review

- Scope: `docs/archive/CYCLE5_T09_REVIEW.md`, T09 admin booking/edit files.
- Why: Admin booking edits touch booking integrity, admin authorization, and client notification integrity.
- Decisions applied: `D-002`, `D-003`, `D-004`
- Evidence collected: initial targeted review findings; notification/reuse fixes; repeat review with no remaining P0/P1 behavior findings; P2 test hardening; full verification.
- Follow-ups: Proceed to T10 reminder scheduler.
- Notes: Stop-Ship: No. P0: 0, P1: 0, P2: 0.

### 2026-06-23 - T10 - Reminder Scheduler

- Scope: `app/scheduler.py`, `app/services/reminders.py`, `app/db/models.py`, `tests/test_reminders.py`, `docs/CODEX_PROMPT.md`, `docs/tasks.md`, `docs/EVIDENCE_INDEX.md`
- Why: Add restart-safe reminder reconstruction and duplicate-send prevention before finance and client-history work begins.
- Decisions applied: `D-002`, `D-004`
- Evidence collected: reminder tests passed; full pytest passed with 47 tests; ruff check; ruff format --check; integrity check; skill security gate.
- Follow-ups: T11 should implement completed booking finance using completed statuses and recorded expenses only.
- Notes: Delivery uses a conditional `pending/failed` to `processing` claim before calling the external sender, then records sent/failed/skipped state.

### 2026-06-23 - Cycle 6 - Targeted T10 Review

- Scope: `docs/archive/CYCLE6_T10_REVIEW.md`, T10 reminder scheduler files.
- Why: Reminder delivery semantics and restart-safe duplicate prevention touch a review escalation boundary.
- Decisions applied: `D-002`, `D-004`
- Evidence collected: initial targeted review findings; atomic claim/timezone/restart/race fixes; repeat review with no remaining P0/P1/P2 findings; full verification.
- Follow-ups: Proceed to T11 completion, expenses, and revenue.
- Notes: Stop-Ship: No. P0: 0, P1: 0, P2: 0.

### 2026-06-23 - T11 - Completion, Expenses, And Revenue

- Scope: `app/services/finance.py`, `app/bot/handlers/admin.py`, `tests/test_finance.py`, `docs/CODEX_PROMPT.md`, `docs/tasks.md`, `docs/EVIDENCE_INDEX.md`
- Why: Add deterministic booking completion and weekly gross/net revenue calculations from completed bookings and recorded expenses.
- Decisions applied: `D-002`, `D-004`
- Evidence collected: finance tests passed; full pytest passed with 52 tests; ruff check; ruff format --check; integrity check; skill security gate.
- Follow-ups: T12 should calculate client history from completed booking final amounts only.
- Notes: Weekly gross/net excludes cancelled, no-show, draft, confirmed, and out-of-week bookings.

### 2026-06-23 - Cycle 7 - Targeted T11 Review

- Scope: `docs/archive/CYCLE7_T11_REVIEW.md`, T11 finance files.
- Why: Financial calculations are a contract escalation boundary.
- Decisions applied: `D-002`, `D-004`
- Evidence collected: targeted review reported no P0/P1/P2 findings; full verification.
- Follow-ups: Proceed to T12 client history.
- Notes: Stop-Ship: No. P0: 0, P1: 0, P2: 0.

### 2026-06-23 - T12 - Client History

- Scope: `app/services/clients.py`, `app/bot/handlers/admin.py`, `tests/test_client_history.py`, `docs/CODEX_PROMPT.md`, `docs/tasks.md`, `docs/EVIDENCE_INDEX.md`
- Why: Add admin client-card and visit-history summaries using completed booking final amounts only.
- Decisions applied: `D-002`, `D-004`
- Evidence collected: client-history tests passed; full pytest passed with 56 tests; ruff check; ruff format --check; integrity check; skill security gate.
- Follow-ups: T13 should document deployment, operator use, backups, rollback, and safe testing rules.
- Notes: Client total spent excludes cancelled, no-show, confirmed, missing-final-amount, and other-client bookings.

### 2026-06-23 - Cycle 8 - Targeted T12 Review

- Scope: `docs/archive/CYCLE8_T12_REVIEW.md`, T12 client-history files.
- Why: Client total spent is covered by the financial calculations contract.
- Decisions applied: `D-002`, `D-004`
- Evidence collected: targeted review reported no P0/P1/P2 findings; full verification.
- Follow-ups: Proceed to T13 deployment and operator guide.
- Notes: Stop-Ship: No. P0: 0, P1: 0, P2: 0.

### 2026-06-23 - T13 - Deployment And Operator Guide

- Scope: `README.md`, `docs/ADMIN_GUIDE.md`, `docs/DEPLOYMENT.md`, `docs/CODEX_PROMPT.md`, `docs/tasks.md`, `docs/EVIDENCE_INDEX.md`
- Why: Close the v1 task graph with local setup, runtime configuration, bot startup, admin operation, deployment, backup, rollback, and safe-testing documentation.
- Decisions applied: `D-001`, `D-002`, `D-003`, `D-004`
- Evidence collected: integrity check; deployment-notes acceptance check; full pytest passed with 56 tests; ruff check; ruff format --check; skill security gate.
- Follow-ups: No implementation tasks remain in the current graph. Future production migration or external integration work needs an explicit task, backup note, and rollback note.
- Notes: Fresh database schema initialization is documented with the existing `create_all` helper; backup/restore docs use a libpq-compatible `DATABASE_BACKUP_URL`.

### 2026-06-23 - Cycle 9 - Targeted T13 Review

- Scope: `docs/archive/CYCLE9_T13_REVIEW.md`, T13 deployment/operator documentation.
- Why: Deployment, secrets, backup, and rollback docs are a contract escalation boundary.
- Decisions applied: `D-001`, `D-002`, `D-003`, `D-004`
- Evidence collected: initial targeted review findings; schema initialization and backup URL docs fixes; repeat review with no remaining P0/P1/P2 findings; full verification.
- Follow-ups: Keep deployment docs current before real client use.
- Notes: Stop-Ship: No. P0: 0, P1: 0, P2: 0.

### 2026-06-23 - Local Telegram Testing Setup And UX Localization

- Scope: `.gitignore`, `README.md`, `docs/ARCHITECTURE.md`, `docs/DEPLOYMENT.md`, `app/config.py`, `app/main.py`, `app/bot/*`, `app/services/booking.py`, `tests/*`
- Why: Prepare the bot for live Telegram testing with the supplied local credentials, 2026-06-27 haircut slots, Russian client/admin UX, map links, client self-service booking management, and admin client/schedule controls.
- Decisions applied: `D-001`, `D-002`, `D-003`, `D-004`
- Evidence collected: ruff check; ruff format --check; full pytest passed with 62 tests; integrity check; skill security gate; local smoke-check for client start/date buttons and admin schedule; bot process started with PID recorded in `bot.pid`.
- Follow-ups: Before real client use, configure durable hosting/process supervision and a backup path for the local database.
- Notes: No payments, calendar sync, external AI behavior, or new admin users were added.

### 2026-06-23 - Runtime Reminder Delivery

- Scope: `app/main.py`, `app/scheduler.py`, `app/services/reminders.py`, `app/bot/messages.py`, `tests/test_reminders.py`, `tests/test_notifications.py`, `README.md`, `docs/CODEX_PROMPT.md`, `docs/EVIDENCE_INDEX.md`
- Why: Connect the existing reminder scheduling service to the live bot runtime so 24h and 3h reminders are delivered automatically.
- Decisions applied: `D-002`, `D-004`
- Evidence collected: ruff check; ruff format --check; full pytest passed with 66 tests; integrity check; skill security gate; `shishki-bot.service` restarted and active; reminder logs present for the current future booking.
- Follow-ups: Monitor first live reminder delivery in `reminder_logs` and `journalctl -u shishki-bot.service`.
- Notes: SQLite naive datetimes are treated as the business timezone for reminder due checks.

### 2026-06-24 - Client About Master Card

- Scope: `about_me.md`, `IMG_9385.PNG`, `app/bot/keyboards.py`, `app/bot/handlers/client.py`, `tests/test_client_handlers.py`, `docs/CODEX_PROMPT.md`, `docs/EVIDENCE_INDEX.md`
- Why: New clients need a low-friction way to learn about the stylist before booking.
- Decisions applied: `D-002`
- Evidence collected: fresh pull from `main`; ruff check; ruff format --check; full pytest passed with 67 tests; integrity check; skill security gate; `shishki-bot.service` restarted and active.
- Follow-ups: Referral mechanics should start as a manual/text offer before adding tracking automation.
- Notes: The about card sends the profile photo with the pulled markdown text as the caption and gives booking/contact buttons.

### 2026-06-24 - T14 - Referral Tracking And Bonuses

- Scope: `app/db/models.py`, `app/services/referrals.py`, `app/services/finance.py`, `app/bot/keyboards.py`, `app/bot/handlers/client.py`, `app/bot/handlers/admin.py`, `app/scheduler.py`, `tests/test_referrals.py`, client/admin/model tests, and operator docs.
- Why: Clients need a personal referral link, and the stylist needs automatic referral attribution plus reminders when a cosmetics/styling bonus is earned.
- Decisions applied: `D-002`, `D-003`, `D-004`
- Evidence collected: ruff check; ruff format --check; full pytest passed with 73 tests; integrity check; skill security gate.
- Follow-ups: Monitor the first live referral deep-link flow and the first pending bonus notification in systemd logs.
- Notes: Schema change is additive only: `referral_codes`, `referrals`, and `referral_bonuses`. Fresh backup is required before applying `create_all` to an existing live database; rollback is app rollback plus optional explicit dropping of the new referral tables if referral data can be discarded.

### 2026-06-24 - T15 - Client Service Menu And Booking Guard

- Scope: `app/bot/keyboards.py`, `app/bot/handlers/client.py`, `tests/test_client_handlers.py`, and client-flow docs.
- Why: Clients need to choose between haircut, coloring, and consultation before booking, and the stylist needs basic protection from one client holding many same-day haircut slots.
- Decisions applied: `D-002`, `D-003`, `D-004`
- Evidence collected: ruff check; ruff format --check; full pytest passed with 75 tests; integrity check; skill security gate.
- Follow-ups: Consider stronger anti-abuse controls after live testing, such as total active booking limits, cooldown after repeated cancellations, admin approval for suspicious users, or deposits for new clients.
- Notes: No schema change. The guard blocks more than 2 active self-booked haircuts on one business date for a Telegram client; admin manual bookings remain operator-controlled.

### 2026-06-24 - T16 - Client UX Copy Cleanup

- Scope: `app/bot/keyboards.py`, `app/bot/handlers/client.py`, `app/bot/messages.py`, `tests/test_client_handlers.py`, `tests/test_notifications.py`, and handoff docs.
- Why: The first client screen was overloaded, referral next actions felt out of context, and the active booking screen repeated a confirmation hint even though action buttons were already visible.
- Decisions applied: `D-002`, `D-003`
- Evidence collected: ruff check; ruff format --check; full pytest passed with 75 tests; integrity check; skill security gate.
- Follow-ups: Test the live `/start`, referral, and `Моя запись` paths in Telegram for copy fit and button order.
- Notes: No schema change. Main menu now focuses on service/account choices only; referral entry points remain after booking and from active booking.

### 2026-06-24 - T17 - Client Flow Consistency Cleanup

- Scope: `app/bot/handlers/client.py`, `tests/test_client_handlers.py`, and client-flow docs.
- Why: The first greeting still showed too much detail, and secondary screens such as `О мастере`, coloring, consultation, no-active-booking, cancellation, and reschedule paths could leave clients with haircut-only or no follow-up navigation.
- Decisions applied: `D-002`, `D-003`
- Evidence collected: ruff check; ruff format --check; full pytest passed with 76 tests; integrity check; skill security gate.
- Follow-ups: Smoke-test `/start`, `О мастере`, `Окрашивание`, `Консультация`, `Моя запись`, cancel, and reschedule paths in Telegram.
- Notes: No schema change. Price and duration remain in slot confirmation/booking detail copy, not in the first greeting.

### 2026-06-24 - T18 - Manual Booking And Official Slots

- Scope: `app/services/booking.py`, `app/bot/handlers/client.py`, `app/bot/handlers/admin.py`, booking/client/admin tests, admin docs, handoff docs, and live local SQLite schedule data.
- Why: Admin needs a practical way to create complex/manual bookings, client contact-intent needs to be visible in client cards, and active bookings must hide every overlapping self-booking slot, not only the exact starting slot.
- Decisions applied: `D-002`, `D-003`, `D-004`
- Evidence collected: targeted booking/client/admin tests; ruff check; ruff format --check; full pytest passed with 79 tests; integrity check; skill security gate; systemd service restarted and active.
- Data operation: stopped `shishki-bot.service`, backed up `shishki_bot.db` to `<private-backup-path>`, cleared 1 test booking, 10 test slots, 2 reminder logs, and 1 status-history row, then created 17 official slots.
- Official slots: 2026-06-28 Sunday hourly starts 13:00 through 19:00; 2026-07-04 Saturday hourly starts 10:00 through 19:00; place is `Сулхана Цинцадзе 22, м. Технический Университет`.
- Follow-ups: Smoke-test `/book`, `/admin` -> `Клиенты`, and the client stale-slot conflict in Telegram before a large announcement.
- Notes: No schema migration. `/book` creates/logs a client confirmation attempt and relies on existing client cards; clients create a card by pressing `/start`, `Окрашивание`, or `Консультация`.

### 2026-06-25 - T19 - Admin Booking Event Notifications

- Scope: `app/bot/handlers/client.py`, `tests/test_client_handlers.py`, and client-booking docs.
- Why: Client self-booking confirmed appointments but did not notify the admin, and client-driven reschedule/cancel events also needed explicit admin visibility.
- Decisions applied: `D-002`, `D-004`
- Evidence collected: targeted client handler tests; ruff check; ruff format --check; full pytest passed with 81 tests; integrity check; skill security gate; systemd service restarted and active.
- Data operation: found 1 existing booking without an `admin_new_booking` log, sent one backfill admin notification, and recorded a `sent` notification log.
- Follow-ups: Monitor `notification_logs` for `admin_new_booking`, `admin_booking_rescheduled`, and `admin_booking_cancelled` rows after live client actions.
- Notes: No schema migration. Admin notifications are sent after the booking transaction commits; delivery success/failure is stored as `NotificationLog` rows and does not cancel the client booking.

### 2026-06-28 - T20 - Haircut Variants And Admin Slot Closures

- Scope: `app/services/booking.py`, `app/bot/handlers/client.py`, `app/bot/handlers/admin.py`, `app/bot/messages.py`, `app/bot/keyboards.py`, booking/client/admin/notification tests, operator docs, and live local SQLite schedule data.
- Why: Clients need male/female haircut pricing, admin needs to identify who booked and book by username, and the live schedule needs operational controls for closing free time.
- Decisions applied: `D-002`, `D-003`, `D-004`
- Evidence collected: targeted booking/client/admin/notification tests; ruff check; ruff format --check; full pytest passed with 85 tests; integrity check; skill security gate.
- Data operation: stopped `shishki-bot.service`, backed up `shishki_bot.db` to `<private-backup-path>`, closed free 2026-07-04 slots at 16:00, 17:00, 18:00, and 19:00, and created 20 slots for 2026-07-08 and 2026-07-10 hourly starts 10:00 through 19:00.
- Live schedule check: 2026-07-04 has active bookings at 14:00 and 15:00, so client-visible open starts are 10:00 through 13:00; 2026-07-08 and 2026-07-10 show 10:00 through 19:00.
- Follow-ups: Smoke-test `/book @username`, `/close`, `/close_day`, and one male/female client booking path in Telegram after restart.
- Notes: No schema migration. Existing legacy `haircut` bookings remain readable; new self-booked haircuts store `haircut_male` or `haircut_female`.

### 2026-06-28 - T21 - Admin Dashboard And Price-Free Reminders

- Scope: `app/bot/handlers/admin.py`, `app/bot/keyboards.py`, `app/bot/messages.py`, admin/auth/notification tests, and operator/product docs.
- Why: Admin needs one useful main menu for bookings, people, and metrics, and client reminders should not mention price.
- Decisions applied: `D-002`, `D-003`, `D-004`
- Evidence collected: targeted admin/auth/notification/reminder tests; ruff check; ruff format --check; full pytest passed with 86 tests; integrity check; skill security gate.
- Follow-ups: Smoke-test `/admin`, `Метрики`, `Клиенты`, and `Записи` in Telegram after restart.
- Notes: No schema migration. Move/cancel remains available from booking detail rather than as standalone main-menu actions.

### 2026-06-30 - T22 - Admin Working Time Reopen And Referral Start CTA

- Scope: `app/bot/handlers/admin.py`, `app/bot/handlers/client.py`, `app/bot/keyboards.py`, admin/client tests, operator/product docs, and live local SQLite schedule data.
- Why: Admin needs to create or reopen working days after schedule changes, and new clients should see the referral bonus entry point immediately on start.
- Decisions applied: `D-002`, `D-003`, `D-004`
- Evidence collected: targeted admin/client menu tests; ruff check; ruff format --check; full pytest passed with 87 tests; integrity check; skill security gate.
- Data operation: stopped `shishki-bot.service`, backed up `shishki_bot.db` to `<private-backup-path>`, confirmed 2026-07-10 had 10 already-closed slots and no active bookings, then created 10 hourly 2026-07-12 slots for starts 10:00 through 19:00.
- Live schedule check: client-visible slots for 2026-07-10 are empty; client-visible slots for 2026-07-12 are 10:00 through 19:00.
- Follow-ups: Smoke-test `/open_day`, `/open`, `/close_day`, and `/start` in Telegram after restart.
- Notes: No schema migration. Opening a slot with an active overlapping booking does not make it client-bookable because the existing availability query hides active booking overlaps.

### 2026-06-30 - T23 - Admin Callback Button Runtime Coverage

- Scope: `app/bot/handlers/admin.py`, `tests/test_admin_booking.py`, and handoff docs.
- Why: Admin dashboard buttons previously had static construction coverage but not a regression test that pressed each callback payload through the runtime dispatch path.
- Decisions applied: `D-002`, `D-003`
- Evidence collected: targeted admin callback test; ruff check; ruff format --check; full pytest passed with 88 tests; integrity check; skill security gate.
- Follow-ups: Smoke-test main admin buttons in Telegram after restart.
- Notes: No schema migration. Router behavior now calls the same `dispatch_admin_callback_payload` helper covered by tests.
