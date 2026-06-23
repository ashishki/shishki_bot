# shishki_bot

Standard-mode AI Workflow Playbook scaffold for a Telegram booking and
lightweight operations bot for one stylist.

## Start Here

- `docs/PROJECT_BRIEF.md` - product brief and constraints.
- `docs/ARCHITECTURE.md` - architecture and mode decision.
- `docs/spec.md` - product behavior and acceptance criteria.
- `docs/tasks.md` - implementation task graph.
- `docs/CODEX_PROMPT.md` - current Codex handoff state.
- `docs/IMPLEMENTATION_CONTRACT.md` - implementation rules.

## Current Verification

```bash
python3 tools/integrity_check.py --root .
python3 tools/skill_security_gate.py --root . --discover-agent-skills --require-scanner
```

T01/T02 will add the Python package, tests, ruff, and full app CI.

## Workflow

This repository uses Codex for implementation. Claude Code slash commands are
not required. If a playbook instruction mentions `/bootstrap-new`, use
`docs/CODEX_PROMPT.md` and `docs/tasks.md` as the Codex equivalent entrypoint.
