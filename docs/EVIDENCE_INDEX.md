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

## Retrieval Rules

- Prefer task-specific tests once implementation begins.
- Add evidence rows when a task produces tests, review reports, deployment
  checks, or migration proof.
- Remove or correct rows that point to stale/missing artifacts.
