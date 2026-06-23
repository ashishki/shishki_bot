# Decision Log - shishki_bot

Version: 1.0
Last updated: 2026-06-23

This file is an index. Canonical sources named in each row win on conflict.

| ID | Date | Status | Decision | Why it matters | Canonical source | Supersedes |
|----|------|--------|----------|----------------|------------------|------------|
| D-001 | 2026-06-23 | Active | Use Standard playbook mode. | The bot is customer-facing and stores booking, client, notification, and finance data; Lean is too light, Strict is not yet justified. | `docs/ARCHITECTURE.md#mode-decision` | none |
| D-002 | 2026-06-23 | Active | Production v1 is deterministic, with no LLM/agent behavior. | Booking, notifications, status, and finance must be predictable and testable. | `docs/ARCHITECTURE.md#deterministic-boundaries` | none |
| D-003 | 2026-06-23 | Active | Codex is the implementation surface; Claude Code command flow is optional and not used now. | Bootstrap must not require `.claude` settings, commands, or hooks. | `docs/PROJECT_BRIEF.md` | none |
| D-004 | 2026-06-23 | Active | PostgreSQL preferred for production; SQLite acceptable only for prototype/local tests. | Durable concurrent booking writes matter more than minimal setup once real clients use the bot. | `docs/ARCHITECTURE.md#tech-stack` | none |

## Retrieval Notes

Read this file before revisiting governance mode, runtime, data storage,
external integrations, or AI usage.
