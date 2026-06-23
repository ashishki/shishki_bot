# shishki_bot Docs

Status: active

## Purpose

This directory holds the Standard AI Workflow Playbook artifacts for
`shishki_bot`.

## Start Here

- `docs/PROJECT_BRIEF.md` - the brief to fill before implementation decisions.
- `docs/ARCHITECTURE.md` - architecture and mode decision.
- `docs/spec.md` - product behavior and acceptance criteria.
- `docs/tasks.md` - the execution queue and verification state.
- `docs/IMPLEMENTATION_CONTRACT.md` - Standard implementation boundary.
- `docs/CODEX_PROMPT.md` - Codex handoff prompt and current working state.
- `AGENTS.md` - repo-local agent instructions.

## Current State

- Phase 1 Standard bootstrap is active.
- Application code has not started.
- Production v1 is deterministic: no RAG, no production LLM behavior, no
  autonomous agent runtime.

## Key Decisions

- Standard mode selected after the brief expanded into a customer-facing booking
  and lightweight operations system.
- No external skills, dynamic routing, persistent agents, or privileged runtime
  changes are approved.
- Codex is the implementation surface; Claude Code command flow is not required.

## Contracts, Proof, and Evals

- `docs/IMPLEMENTATION_CONTRACT.md` - required boundaries for Standard-mode implementation work.
- `docs/COST_BUDGET.md` - budget boundary to complete once AI/model usage is known.
- `docs/DECISION_LOG.md` - decision retrieval index.
- `docs/IMPLEMENTATION_JOURNAL.md` - session/task continuity log.
- `docs/EVIDENCE_INDEX.md` - durable proof index.
- `tools/integrity_check.py` - deterministic reference integrity check.

## Active Tasks

- `docs/tasks.md` - T01 is Project Skeleton.

## Known Gaps

- The project-specific application stack and test command are not defined yet.
  T01/T02 create them.

## Authority

This README is a navigation index. Canonical artifacts, tests, evals, ADRs,
proof receipts, and review reports remain authoritative.
