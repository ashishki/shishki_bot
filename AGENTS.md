# AGENTS.md

Mode: Standard
Version: 1.0
Date: 2026-06-23

## Current State

- Phase: 1
- Baseline: Standard bootstrap complete; no application code yet.
- Primary handoff: `docs/CODEX_PROMPT.md`
- Current task graph: `docs/tasks.md`
- Contract: `docs/IMPLEMENTATION_CONTRACT.md`
- Verification command: `python3 tools/integrity_check.py --root .`
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

T01: Project Skeleton
