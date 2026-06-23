# Evidence Index - shishki_bot

Version: 1.0
Last updated: 2026-06-23

This index points to durable proof. It is not proof by itself.

| Topic / Task | Artifact type | Location | Scope covered | Last verified | Canonical? |
|--------------|---------------|----------|---------------|---------------|------------|
| Bootstrap integrity | command | `tools/integrity_check.py` | Playbook reference integrity. Command: python3 tools/integrity_check.py --root . | 2026-06-23 | Yes |
| External skill boundary | command | `tools/skill_security_gate.py` | Confirms no untrusted external skills are active. Command: python3 tools/skill_security_gate.py --root . --discover-agent-skills --require-scanner | 2026-06-23 | Yes |
| Phase 1 validation | audit | `docs/audit/PHASE1_AUDIT.md` | Standard Phase 1 artifact validation before T01 | 2026-06-23 | Yes |
| T01 project skeleton | tests | `tests/test_config.py`, `tests/test_imports.py` | Settings load from supplied environment; app import has no Telegram side effects. Commands run: ruff check, ruff format --check, pytest tests -q, integrity check, skill security gate. | 2026-06-23 | Yes |
| T02 local and CI verification | workflow/docs | `.github/workflows/ci.yml`, `README.md`, `docs/CODEX_PROMPT.md` | CI and local commands run ruff check, ruff format --check, pytest, integrity check, and external skill security gate. | 2026-06-23 | Yes |
| T03 smoke baseline | tests | `tests/test_config.py`, `tests/test_imports.py` | Test settings ignore real environment values when supplied a source; importing `app.main` does not import `aiogram`. | 2026-06-23 | Yes |
| T04 database model baseline | tests | `tests/test_models.py`, `app/db/models.py`, `app/db/session.py` | SQLAlchemy metadata creates/drops all tables; minimal booking graph includes users, clients, slots, status history, notification logs, reminder logs, and booking expenses; booking statuses match architecture. | 2026-06-23 | Yes |
| Phase 1 review archive | audit | `docs/archive/PHASE1_REVIEW.md`, `docs/audit/PHASE_REPORT_LATEST.md` | Deep review for Phase 1 T01-T04. Stop-Ship: No. P0: 0, P1: 0, P2: 2. | 2026-06-23 | Yes |
| T05 booking service | tests | `tests/test_booking_service.py`, `tests/test_models.py`, `app/services/booking.py` | Confirmed haircut booking defaults to 90 GEL and 60 minutes; double booking is rejected; coloring self-booking is rejected; past/blocked/booked slots are filtered or rejected; booking slot is non-null; async session helpers commit/rollback. | 2026-06-23 | Yes |
| Cycle 2 T05 targeted review | audit | `docs/archive/CYCLE2_T05_REVIEW.md` | Deep review for T05 booking transaction and slot locking. Stop-Ship: No. P0: 0, P1: 0, P2: 0. | 2026-06-23 | Yes |
| T06 notifications | tests | `tests/test_notifications.py`, `app/bot/messages.py`, `app/services/notifications.py` | Confirmation, reschedule, cancellation, and admin booking templates include appointment details in business timezone; notification service logs sent, failed delivery, and missing Telegram identity attempts with fake sender tests. | 2026-06-23 | Yes |
| Cycle 3 T06 targeted review | audit | `docs/archive/CYCLE3_T06_REVIEW.md` | Deep review for T06 notification delivery semantics. Stop-Ship: No. P0: 0, P1: 0, P2: 0. | 2026-06-23 | Yes |
| T07 admin authorization | tests | `tests/test_admin_auth.py`, `app/bot/handlers/admin.py`, `app/bot/keyboards.py`, `app/main.py` | Admin menu command and admin callback handling require allowlisted Telegram IDs; forged `admin:*` callbacks from non-admin users are denied; malformed callback payloads are rejected; admin menu exposes today, this week, manual booking, change booking, cancel booking, revenue, and clients actions. | 2026-06-23 | Yes |
| Cycle 4 T07 targeted review | audit | `docs/archive/CYCLE4_T07_REVIEW.md` | Deep review for T07 admin authorization boundary. Initial P1/P2 findings were fixed and repeat review reported no remaining P0/P1/P2 findings. Stop-Ship: No. P0: 0, P1: 0, P2: 0. | 2026-06-23 | Yes |
| T08 client booking handlers | tests | `tests/test_client_handlers.py`, `app/bot/handlers/client.py`, `app/bot/keyboards.py`, `app/main.py` | Start and unknown input return the client menu; haircut callback flow lists slots, requires explicit confirmation before booking, and commits only on confirm; complex-service callback creates no booking and includes stylist contact link; stale slot callbacks are recoverable; active booking lookup ignores past bookings; runtime async session dispatch is covered. | 2026-06-23 | Yes |
| T09 admin booking edits | tests | `tests/test_admin_booking.py`, `app/services/booking.py`, `app/bot/handlers/admin.py`, `app/bot/messages.py`, `app/db/models.py` | Admin allowlisted manual complex bookings support custom duration/price; reschedule and cancel write status history and send/log client notifications; client-visible detail edits require notification sender and log delivery; occupied-slot reschedule fails without notification; cancelled slots can be reused; whitespace place and late IntegrityError paths are covered. | 2026-06-23 | Yes |
| Cycle 5 T09 targeted review | audit | `docs/archive/CYCLE5_T09_REVIEW.md` | Targeted review for admin booking edits, notification integrity, slot reuse, and admin authorization. Initial P1/P2 findings were fixed; repeat/final checks reported no remaining P0/P1/P2 behavior findings. Stop-Ship: No. P0: 0, P1: 0, P2: 0. | 2026-06-23 | Yes |
| T10 reminder scheduler | tests | `tests/test_reminders.py`, `app/services/reminders.py`, `app/scheduler.py`, `app/db/models.py` | Reminder times are calculated at 24h and 3h before appointment; restart recovery rebuilds pending/failed reminder logs; persisted sent reminders are not recovered; delivery uses an atomic processing claim to prevent duplicate sends from stale sessions; rescheduled bookings reconcile reminder times; scheduler returns detached-safe UTC DTOs. | 2026-06-23 | Yes |
| Cycle 6 T10 targeted review | audit | `docs/archive/CYCLE6_T10_REVIEW.md` | Targeted review for reminder recovery, notification delivery semantics, restart behavior, and duplicate-send prevention. Initial P1/P2 findings were fixed; repeat review reported no remaining P0/P1/P2 findings. Stop-Ship: No. P0: 0, P1: 0, P2: 0. | 2026-06-23 | Yes |
| T11 finance | tests | `tests/test_finance.py`, `app/services/finance.py`, `app/bot/handlers/admin.py` | Admin can complete bookings with final amount and expenses; weekly gross revenue counts completed booking final amounts only; net revenue subtracts recorded expenses from completed bookings; cancelled/no-show/confirmed bookings are excluded; admin finance wrappers require allowlist. | 2026-06-23 | Yes |
| Cycle 7 T11 targeted review | audit | `docs/archive/CYCLE7_T11_REVIEW.md` | Targeted review for financial calculations, completion status transitions, admin authorization, and tests. Review reported no P0/P1/P2 findings. Stop-Ship: No. P0: 0, P1: 0, P2: 0. | 2026-06-23 | Yes |

## Retrieval Rules

- Prefer task-specific tests once implementation begins.
- Add evidence rows when a task produces tests, review reports, deployment
  checks, or migration proof.
- Remove or correct rows that point to stale/missing artifacts.
