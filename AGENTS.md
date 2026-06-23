# AGENTS.md

Mode: Standard
Version: 1.0
Date: 2026-06-23

## Current State

- Phase: 4
- Baseline: T11 complete; finance tests pass with 52 total tests.
- Primary handoff: `docs/CODEX_PROMPT.md`
- Current task graph: `docs/tasks.md`
- Contract: `docs/IMPLEMENTATION_CONTRACT.md`
- Verification command: full README verification: ruff check, ruff format --check,
  pytest, integrity check, and skill security gate.
- External skills: none approved.

## Instructions For Codex

1. Read `docs/CODEX_PROMPT.md` before starting implementation work.
2. Read the active task in `docs/tasks.md` and its `Context-Refs`.
3. Follow `docs/IMPLEMENTATION_CONTRACT.md`.
4. Keep edits inside the active task scope unless verification reveals a required dependency.
5. Add or update tests for behavior changes.
6. Run the task verification before reporting completion.
7. Do not require Claude Code, `.claude` commands, or Claude hooks for v1.
8. Stop for human approval before adding payments, external integrations,
   production AI behavior, new admin users, or risky data migrations.

## Current Next Task

T12: Client History
