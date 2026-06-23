# Adoption Modes

## Purpose

The playbook has three adoption modes. The mode decides which artifacts,
validators, review gates, and evidence records are justified for the project.

Do not use Strict mode language to run a Lean project. Do not create placeholder
artifacts only to satisfy a checklist.

## Mode Selection

| Mode | Use When | Do Not Use When |
|------|----------|-----------------|
| Lean | Prototype, internal helper, low-blast-radius workflow, paused/reference repo | The system handles PII, privileged tools, compliance evidence, or autonomous runtime changes |
| Standard | Internal operational system, recoverable customer-facing service, normal RAG/tool-use feature work | The work is a one-off script or docs-only update |
| Strict | High-blast-radius, compliance-heavy, privileged tool-use, persistent agent runtime, risky migration | The risk model is vague or the team will not maintain the evidence trail |

## Required Artifacts

Use `tools/init_playbook_project.py` to create the selected kit when starting a
new or retrofit repository. The table below still defines authority; the tool is
only the copier/scaffolder.

| Artifact | Lean | Standard | Strict |
|----------|------|----------|--------|
| Problem fit note | Required | Required | Required |
| `docs/tasks.md` | Required | Required | Required |
| `docs/CODEX_PROMPT.md` or `AGENTS.md` | Required | Required | Required |
| `docs/IMPLEMENTATION_CONTRACT.md` | Contract-lite | Required | Required |
| CI or documented local verification command | Required | Required CI | Required CI with relevant gates |
| `docs/ARCHITECTURE.md` | Optional unless architecture is changing | Required | Required |
| `docs/spec.md` | Optional for small task sets | Required | Required |
| `docs/DECISION_LOG.md` | Optional | Required | Required |
| `docs/IMPLEMENTATION_JOURNAL.md` | Optional | Required | Required |
| `docs/README.md` / README indexes | Required when docs/subsystems are non-trivial | Required | Required |
| `docs/COGNITION_MANIFEST.md` | Optional | Optional | Required when context packets/vault are used |
| `docs/EVIDENCE_INDEX.md` | Optional | Optional unless recurring evidence exists | Required |
| Capability eval artifacts | Only for active capability behavior | Only for active capability behavior | Required for active capability behavior |
| Runtime verification record | Risky edits only | Risky edits and phase boundaries | Required for privileged/risky writes |
| Cost budget | Inline for AI tasks | Required for recurring AI use | Required |
| AI cost architecture | Inline when recurring/material AI, caching, routing, batch, or cascades are used | Required when recurring/material AI, caching, routing, batch, or cascades are used | Required when AI/model work is active |
| Router eval | Optional; only if dynamic routing/cascades are used | Required before dynamic routing/cascades | Required before dynamic routing/cascades |
| External skill trust record | Inline only for project-local instruction-only low-risk skills | Required before external skill install/update/enablement | Required before external skill install/update/enablement |
| Deep multi-agent review | Optional | Phase/risk boundary | Phase/risk boundary and high-risk changes |

## Validator Scope

The Phase 1 validator must run in the selected mode:

- Lean: block only on missing task state, missing verification command, vague
  acceptance criteria, missing implementation boundaries, or unresolved
  placeholders in required artifacts. For AI tasks, missing budget boundary is
  also a blocker. For recurring/material AI, caching, routing, batch, or
  cascades, missing inline cost architecture notes are a blocker.
  For external skills, missing inline trust evidence is a blocker unless the
  skill is not installed/enabled and is not needed for the first task.
- Standard: run the normal structural and cross-document checks, but treat
  cognition/evidence artifacts as required only when the project uses them. A
  recurring AI workload requires `docs/COST_BUDGET.md` or equivalent budget
  section. Recurring/material AI, prompt caching, batch lanes, dynamic routing,
  or cascades require `docs/ai_cost_architecture.md`; dynamic routing/cascades
  require `docs/router_eval.md`.
  External skills require a trust record before installation, update, or
  enablement.
- Strict: run the full artifact, evidence, cognition, evaluation, runtime, and
  review checks, including cost gates and external skill trust records.

## Review Scope

| Change Type | Lean | Standard | Strict |
|-------------|------|----------|--------|
| Docs-only navigation update | Deterministic link/state check | Deterministic check; light review if policy changed | Light review if policy/evidence changed |
| Test-only change | Test command and diff check | Light review if fixtures or assertions change behavior | Light review |
| Routine implementation | Light review or maintainer review | Light review | Light review |
| Security/auth/data boundary | Deep review | Deep review | Deep review plus evidence record |
| Runtime/tool/autonomy expansion | Not allowed without mode change | Deep review and ADR | Deep review, ADR, runtime verification |

## Hard Invariants

All modes keep these invariants:

- repo artifacts and code are the source of truth
- no self-review for meaningful implementation changes
- explicit task state
- test or verification evidence before completion
- bounded correction loops
- declared budget boundary for AI/model work
- declared cost architecture boundary for recurring/material AI, caching,
  routing, batch, or cascades
- no external skill is installed, enabled, updated, or globally exposed without
  trust evidence
- human approval at meaningful risk boundaries

Mode selection changes overhead. It does not permit unsupported claims.
