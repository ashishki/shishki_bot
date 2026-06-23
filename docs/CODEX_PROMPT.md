# CODEX_PROMPT.md

Version: 1.0
Date: 2026-06-23
Mode: Standard
Phase: 1

## Current State

- Phase: 1
- Baseline: T01 complete; project skeleton exists with 2 smoke tests passing.
- Ruff: configured in `pyproject.toml` for `app/` and `tests/`.
- CI: scaffold can install dev dependencies after T01; T02 owns the full CI/README verification update.
- Last verification: 2026-06-23 - ruff check, ruff format --check, pytest `tests -q` (2 passed), integrity check, and skill security gate passed.
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

T02: CI And Local Verification

Before editing, read:

- `docs/tasks.md#t02-ci-and-local-verification`
- `docs/IMPLEMENTATION_CONTRACT.md`
- `docs/ARCHITECTURE.md#tech-stack`

## Verification

Current local verification:

```bash
/tmp/shishki_bot_venv/bin/python -m ruff check app tests
/tmp/shishki_bot_venv/bin/python -m ruff format --check app tests
/tmp/shishki_bot_venv/bin/python -m pytest tests -q
python3 tools/integrity_check.py --root .
python3 tools/skill_security_gate.py --root . --discover-agent-skills --require-scanner
```

T02 must update CI and README with the full local verification command using the
project's documented environment setup.

## Fix Queue

empty

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

none

## Completed Tasks

- 2026-06-23 - T01 Project Skeleton: added package metadata, runtime/dev
  requirements, `app/config.py`, side-effect-free `app/main.py`, and smoke
  tests for settings and imports.

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
