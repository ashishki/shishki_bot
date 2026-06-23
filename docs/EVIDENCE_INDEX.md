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

## Retrieval Rules

- Prefer task-specific tests once implementation begins.
- Add evidence rows when a task produces tests, review reports, deployment
  checks, or migration proof.
- Remove or correct rows that point to stale/missing artifacts.
