# Architecture - shishki_bot

Version: 1.0
Last updated: 2026-06-23
Status: Phase 2 implementation ready

## Mode Decision

Selected mode: Standard.

Standard is proportionate because the system is a customer-facing Telegram bot
that stores client identifiers, booking history, appointment status, client
notifications, and basic business finance data. Lean was enough for the initial
brief, but the current scope now needs durable architecture, task graph, CI, and
implementation contract. Strict is not required yet because there is no
regulated data, no payment processing, no autonomous runtime, no privileged
tool-use, and no compliance evidence gate.

Cost budget: `docs/COST_BUDGET.md` exists for development governance, but
production v1 is deterministic and should not use LLM inference.

External skills: none planned. No trust record is required unless a third-party
or cross-project skill is proposed later.

## System Overview

`shishki_bot` is a single-stylist Telegram booking and lightweight operations
bot. Clients use it to book simple services, receive appointment confirmations,
and get reminders or change notifications. The stylist uses an admin menu to
manage availability, create manual bookings for complex services, edit/cancel
appointments, record final amounts and basic expenses, and view weekly revenue
and client history.

The system should be deterministic. Booking rules, reminders, notifications,
financial summaries, and status transitions must be implemented as normal
application logic, not AI behavior.

## Problem Fit and Adoption Reality

| Question | Answer |
|----------|--------|
| Concrete pain | Booking depends on manual chat, availability checks, repeated date/time/place/price messages, reminders, and memory-based client/revenue tracking. |
| Current workaround | Clients write in Telegram/Instagram. The stylist manually coordinates, updates schedule, reminds clients, and tracks revenue/client history separately or from memory. |
| Why current process is insufficient | Chat is poor for reliable status, reminders, reschedules, cancellations, client history, expenses, and weekly revenue. |
| First operator | Stylist / business owner. |
| Adoption failure condition | Bot is confusing, creates more work than chat, double-books, misses notifications, or gives unreliable revenue/client stats. |
| First proof of value | 30-50% of standard haircut bookings come through the bot, confirmations include date/time/place/price, no double bookings occur, and weekly revenue is visible without separate calculation. |

Claims out of bounds before evidence: fully automated salon, AI assistant,
autonomous sales agent, automatic coloring consultation, production-ready CRM.

Human-owned work: coloring consultation, complex service estimates, conflict
handling, schedule responsibility, final financial entries, and business
decisions.

## Solution Shape

| Decision | Selection | Rationale |
|----------|-----------|-----------|
| Primary shape | Deterministic workflow application | The product is menus, state transitions, database writes, scheduled reminders, and summaries. |
| Governance | Standard | Customer-facing app with PII-like Telegram data and financial records. |
| Runtime tier | T1 | A normal container/managed service with a database and scheduler is sufficient. |

### Rejected Lower-Complexity Options

- Lean-only governance: too little structure for customer data, notifications,
  status transitions, and financial reporting.
- Strict governance: unnecessary until payments, regulated data, multi-tenant
  operations, or autonomous runtimes are added.
- AI/agentic runtime: not needed for deterministic booking and reporting.

### Minimum Viable Control Surface

- Admin allowlist for all privileged bot actions.
- Transactional slot locking and booking status history.
- Notification delivery logs for confirmations, reminders, cancellations, and
  reschedules.
- Revenue/client stats calculated from stored completed bookings only.
- CI and local test harness before feature work proceeds beyond Phase 1.

## Runtime and Isolation Model

| Property | Decision |
|----------|----------|
| Isolation | Container or managed process boundary. |
| Persistence | Database-backed. PostgreSQL preferred for production; SQLite acceptable only for a local prototype. |
| Network | Telegram Bot API egress required. Optional future Google Calendar or export integrations require ADR/task update. |
| Secrets | Bot token, admin allowlist, database URL, and webhook secret stored in environment variables. |
| Runtime mutation | No shell/package/toolchain mutation at runtime. |
| Recovery | Bookings and reminder state are recovered from database after restart. |

## Human Approval Boundaries

Human approval is required for:

- cancelling or rescheduling a booking;
- changing final price, duration, place, or service after confirmation;
- manually creating complex-service bookings;
- changing default prices, address/place, or reminder policy;
- adding payments, external integrations, or new admin users;
- any deployment or migration that can affect production data.

## Deterministic vs LLM-Owned Subproblems

| Subproblem | Owner | Rule |
|------------|-------|------|
| Booking validation | Deterministic | Slot must exist, be available, and be locked transactionally. |
| Pricing | Deterministic/admin-entered | Male haircut defaults to 100 GEL, female haircut to 120 GEL; complex services use manual price. |
| Status transitions | Deterministic | Only declared statuses are valid. |
| Notifications | Deterministic | Client notifications are sent from templates after booking changes. |
| Revenue/client stats | Deterministic | Calculated from completed bookings and recorded expenses. |
| AI | Not used | No production behavior depends on LLM output in v1. |

## Booking Statuses

Allowed statuses:

- `draft`
- `confirmed`
- `rescheduled`
- `cancelled_by_client`
- `cancelled_by_admin`
- `completed`
- `no_show`

Every status change must be stored in history with actor, timestamp, old value,
new value, and reason/note when provided.

## Component Table

| Component | Path | Responsibility |
|-----------|------|----------------|
| Bot entrypoint | `app/main.py` | Starts Telegram bot, scheduler, and app wiring. |
| Configuration | `app/config.py` | Environment variables and settings validation. |
| Client handlers | `app/bot/handlers/client.py` | Client menus, booking flow, booking view, cancel/reschedule request flow. |
| Admin handlers | `app/bot/handlers/admin.py` | Admin menu, slot management, manual bookings, edits, stats, client cards. |
| Message templates | `app/bot/messages.py` | Confirmation, reminder, reschedule, cancellation, admin notifications. |
| Services | `app/services/` | Booking, notification, reminder, finance, client history, and referral business logic. |
| Database models | `app/db/models.py` | Users, clients, slots, bookings, status history, expenses, notification/reminder logs, referral codes, referrals, and referral bonuses. |
| Database session | `app/db/session.py` | Engine/session setup and transaction boundary helpers. |
| Scheduler | `app/scheduler.py` | Restart-safe booking reminder scheduling/recovery and one-time admin referral-bonus reminders. |
| Tests | `tests/` | Unit and integration tests for core flows. |

## Data Flow

1. Client opens bot and selects a simple service.
2. Bot reads available slots from database.
3. Client selects slot and confirms.
4. Booking service locks the slot and creates a `confirmed` booking in one transaction.
5. Notification service sends client confirmation and admin notification.
6. Scheduler records reminder jobs based on booking time.
7. Admin can edit/reschedule/cancel booking; each change is persisted, logged,
   and triggers a client notification when relevant.
8. After appointment, admin marks booking completed and records final amount and
   optional expenses.
9. Finance/client services calculate weekly revenue and client history from
   stored completed bookings.
10. If the completed client came through a referral link, the referral is
    qualified; every 3 qualified referrals creates a pending admin bonus for
    professional hair cosmetics.
11. The scheduler sends a one-time admin reminder for newly pending referral
    bonuses, and admin can mark the bonus as awarded.

## Tech Stack

| Area | Choice | Rationale |
|------|--------|-----------|
| Language | Python 3.12 | Existing playbook scripts use Python; strong Telegram ecosystem. |
| Telegram framework | aiogram 3.x | Async, widely used, good callback/menu support. |
| Database | PostgreSQL for production, SQLite for local prototype | PostgreSQL handles durable concurrent writes; SQLite keeps local setup simple. |
| ORM | SQLAlchemy 2.x or SQLModel | Explicit transactions and testable models. |
| Scheduler | APScheduler or database-backed scheduler service | Enough for reminder jobs without adding a queue in v1. |
| Tests | pytest, pytest-asyncio | Standard Python test harness. |
| Lint/format | ruff | Fast and simple CI gate. |
| Deployment | Small VPS/Render/Railway/Fly.io container | Low traffic and simple runtime needs. |
| CI | GitHub Actions | Required Standard verification surface. |

## Security Boundaries

Single-tenant system. Tenant isolation is not applicable.

Admin access is restricted by allowlisted Telegram user IDs. Client identity is
based on Telegram user ID where available. Store only the minimum data needed:
Telegram user ID, username/display name if available, booking history, service
notes, amounts, and expenses.

PII-like fields must not be written to logs unless redacted or represented by
internal IDs. Bot token, database URL, admin IDs, and webhook secret are secrets.

## External Integrations

| Service | Purpose | Auth |
|---------|---------|------|
| Telegram Bot API | Client/admin bot messages and callbacks | Bot token |
| PostgreSQL provider | Durable booking and client/finance records | Database URL |
| Optional Google Calendar | Future calendar sync | OAuth/API credentials; not v1 |
| Optional CSV/Google Sheets export | Future reporting/export | Explicit future task/ADR |

## External Agent Skills

None in v1. If a third-party or cross-project skill is proposed later, create
`docs/security/skills/{skill-name}/TRUST_RECORD.md` before installing or
enabling it.

## Runtime Contract

| Name | Description | Example | Required |
|------|-------------|---------|----------|
| `BOT_TOKEN` | Telegram bot token | `123456:abc` | Yes |
| `ADMIN_TELEGRAM_IDS` | Comma-separated admin Telegram IDs | `111,222` | Yes |
| `DATABASE_URL` | Database connection URL | `postgresql+asyncpg://user:pass@host/db` | Yes |
| `TIMEZONE` | Business timezone | `Asia/Tbilisi` | Yes |
| `DEFAULT_PLACE` | Human-readable appointment place/address | `Studio address` | Yes |
| `STYLIST_CONTACT_URL` | Public stylist contact link for consultation redirects | `https://t.me/stylist` | Yes |
| `DEFAULT_MAP_URL` | Optional map link | `https://maps.example/...` | No |
| `YANDEX_PLACE` / `YANDEX_MAP_URL` | Optional Yandex Maps address link | `https://yandex.example/...` | No |
| `GOOGLE_PLACE` / `GOOGLE_MAP_URL` | Optional Google Maps address link | `https://google.example/...` | No |
| `WEBHOOK_SECRET` | Secret for webhook mode | `change-me` | No |
| `ENV` | Runtime environment | `local` | No |

## File Layout

```text
app/
  main.py
  config.py
  scheduler.py
  bot/
    handlers/
      admin.py
      client.py
    keyboards.py
    messages.py
  db/
    models.py
    session.py
  services/
    booking.py
    clients.py
    finance.py
    notifications.py
    reminders.py
tests/
  test_booking_service.py
  test_notifications.py
  test_finance.py
  test_client_history.py
docs/
  PROJECT_BRIEF.md
  ARCHITECTURE.md
  spec.md
  tasks.md
```

## Capability Profiles

| Profile | Status | Rationale |
|---------|--------|-----------|
| RAG | OFF | No retrieval corpus needed in v1. |
| Tool-use agent | OFF | Telegram/database/scheduler are application integrations, not LLM-directed tools. |
| Agentic loop | OFF | No autonomous planning or loop is needed. |
| Planning | OFF | Structured project tasks exist, but production app does not generate plans. |
| Compliance | OFF | Basic privacy hygiene is required; no named compliance framework is a launch gate. |

## Continuity and Retrieval Model

Canonical documents:

- `docs/PROJECT_BRIEF.md`
- `docs/ARCHITECTURE.md`
- `docs/spec.md`
- `docs/tasks.md`
- `docs/IMPLEMENTATION_CONTRACT.md`
- `docs/CODEX_PROMPT.md`

Convenience/retrieval documents:

- `docs/DECISION_LOG.md`
- `docs/IMPLEMENTATION_JOURNAL.md`
- `docs/EVIDENCE_INDEX.md`

Scoped retrieval rule: start from the task's `Context-Refs` in `docs/tasks.md`.
Use broad repository search only when those references are insufficient.

## Non-Goals

- No online payments in v1.
- No AI consultation or automatic coloring price estimation.
- No multi-stylist scheduling.
- No full CRM, payroll, tax accounting, inventory, or formal bookkeeping.
- No Instagram integration in v1.
- No Google Calendar sync unless added by explicit future task.
- No autonomous agents, dynamic routing, RAG, or LLM production behavior.
