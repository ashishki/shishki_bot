# Implementation Contract - shishki_bot

Status: IMMUTABLE
Version: 1.0
Last updated: 2026-06-23
Mode: Standard

## Purpose

This contract defines the stable implementation rules for `shishki_bot`.
Canonical product behavior is in `docs/spec.md`; architecture decisions are in
`docs/ARCHITECTURE.md`; task execution is in `docs/tasks.md`.

## Universal Rules

- Do not commit secrets, credentials, tokens, `.env` files, database dumps, or
  real client data.
- Do not weaken tests, acceptance criteria, verification commands, or security
  boundaries to make a task pass.
- Do not self-review meaningful implementation changes.
- Do not expand runtime, network, payment, external integration, or autonomous
  behavior without updating architecture/tasks and getting human approval.
- Repository files are source of truth. Chat summaries and generated memory are
  convenience only.
- Every task must run its declared verification command before completion.

## Project-Specific Rules

### Booking Integrity

Booking creation and reschedule must lock the target slot transactionally. A
client cannot reserve an already booked or blocked slot.

Violation: P1.

### Client Notification Integrity

When service, date, time, place, price, status, cancellation, or reschedule
changes after confirmation, the notification service must send or explicitly log
the failed client notification. Silent changes are forbidden.

Violation: P1.

### Admin Authorization

Admin commands must be restricted to `ADMIN_TELEGRAM_IDS`. Client users must not
be able to call admin actions through direct commands or callback payload edits.

Violation: P1.

### Financial Calculations

Weekly revenue, client total spent, and net estimate must be calculated from
completed bookings and recorded expenses only. Cancelled/no-show/draft bookings
must not be counted as completed revenue.

Violation: P1.

### AI Boundary

Production v1 must not use LLMs for booking decisions, pricing, reminders,
financial summaries, status transitions, or client notifications.

Violation: P1.

## Data Classification

PII-like fields in this project:

- Telegram user ID
- Telegram username
- Telegram display name
- booking date/time and service history
- client notes
- amounts paid and per-booking expense notes

These fields may be stored in the application database but must not be logged in
plain text unless the log is local test output with synthetic data.

## Runtime and Secrets

| Boundary | Rule |
|----------|------|
| Secrets | `BOT_TOKEN`, `DATABASE_URL`, `ADMIN_TELEGRAM_IDS`, and webhook secrets live in environment variables. |
| Network | Telegram Bot API egress is allowed. Other integrations require explicit task/architecture update. |
| Runtime mutation | No package/toolchain mutation at runtime. |
| Persistence | Database is canonical for bookings, status history, notification logs, reminders, clients, and expenses. |
| Backups | Production deployment must have a documented backup path before real client use. |

## Continuity and Retrieval Rules

- Canonical sources are `docs/PROJECT_BRIEF.md`, `docs/ARCHITECTURE.md`,
  `docs/spec.md`, `docs/tasks.md`, `docs/IMPLEMENTATION_CONTRACT.md`, and
  `docs/CODEX_PROMPT.md`.
- Retrieval surfaces such as `docs/DECISION_LOG.md`,
  `docs/IMPLEMENTATION_JOURNAL.md`, and `docs/EVIDENCE_INDEX.md` are indexes and
  handoff aids, not higher authority.
- Before implementation, read the active task's `Context-Refs` first.
- Read `docs/DECISION_LOG.md` before changing governance mode, runtime,
  database choice, external integrations, payment scope, or AI usage.

## Control Surface and Runtime Boundaries

| Boundary | Rule |
|----------|------|
| Privileged actions | Admin-only actions require allowlisted Telegram IDs and human ownership. |
| Runtime mutation | No shell/package/toolchain mutation at runtime. |
| External side effects | Telegram messages are allowed only through notification services; tests must use fakes. |
| Data migration | Any production data migration requires explicit task, backup note, and rollback note. |
| Auditability | Booking changes, notification attempts, status changes, final amounts, and expenses must be logged in database records. |

## Mandatory Pre-Task Protocol

1. Read `docs/CODEX_PROMPT.md`.
2. Read the active task and `Context-Refs` in `docs/tasks.md`.
3. Read this contract.
4. Run or record the current baseline verification. Before T01/T02, use
   `python3 tools/integrity_check.py --root .`. After T02, use the full project
   command documented in README.
5. When ruff/pytest are configured, run ruff and pytest before reporting task
   completion.

## Testing Rules

- Core service logic must be testable without Telegram network calls.
- Use fake Telegram sender/adapters in tests.
- Tests must cover double-booking prevention, admin authorization, notification
  triggering, status transitions, revenue calculations, and client history.
- Every bug fix must add or update a regression test unless the fix is docs-only.

## Review Rules

Use Standard review for normal implementation work. Escalate to deeper review
when a task touches:

- admin authorization;
- booking transaction/locking;
- production data migration;
- notification delivery semantics;
- financial calculations;
- external integrations;
- deployment/secrets.

## Forbidden Actions

- Building SQL with string interpolation for user-controlled values.
- Skipping baseline capture when the task requires it.
- Self-closing review findings without code verification.
- Deferring CI setup past Phase 1.
- Expanding runtime tier, network scope, payment scope, or external integration
  scope without architecture and task updates.
- Unauthorized runtime-tier expansion.
- Hardcoding real bot tokens or admin IDs.
- Sending real Telegram messages from automated tests.
- Counting cancelled/no-show bookings as completed revenue.
- Allowing client-controlled callback data to bypass server-side validation.
- Adding payments, external calendar sync, or AI behavior without an explicit
  task and architecture update.
