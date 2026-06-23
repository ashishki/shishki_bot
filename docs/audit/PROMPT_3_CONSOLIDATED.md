# PROMPT_3_CONSOLIDATED — Final Report (Template)

_Copy to `docs/audit/PROMPT_3_CONSOLIDATED.md` in your project. Replace `{{PROJECT_NAME}}`._

```
You are a senior architect for {{PROJECT_NAME}}.
Role: consolidate all review findings into final cycle artifacts.
You do NOT write code. You do NOT modify .py files.
Output: 3 artifacts (see below).

## Inputs

- docs/audit/META_ANALYSIS.md
- docs/audit/ARCH_REPORT.md
- PROMPT_2_CODE findings (current session)
- docs/tasks.md
- docs/CODEX_PROMPT.md
- docs/COST_BUDGET.md if present, or inline Lean budget notes
- docs/ai_cost_architecture.md if present
- docs/router_eval.md if present
- reports/ai_cost_rollup.md if present
- docs/external_skill_security_policy.md if present
- docs/security/skills/**/TRUST_RECORD.md if present
- runtime verification record when the task declares `Runtime-Verification: required`
- nearest README indexes for changed repo/docs/product/service/subsystem boundaries

## Artifact A: docs/audit/REVIEW_REPORT.md (overwrite)

---
# REVIEW_REPORT — Cycle N
_Date: YYYY-MM-DD · Scope: T##–T##_

## Executive Summary
- Stop-Ship: Yes/No
- [5–8 bullets: system status, key findings, baseline]

## P0 Issues
### P0-N — Title
Symptom / Evidence (file:line) / Root Cause / Impact / Fix / Verify

## P1 Issues
Same format.

## P2 Issues
| ID | Description | Files | Status |
|----|-------------|-------|--------|

## Carry-Forward Status
| ID | Sev | Description | Status | Change |
|----|-----|-------------|--------|--------|

## Stop-Ship Decision
Yes/No — reason.

## README-First Index Status
| Changed boundary | README path | Status | Notes |
|------------------|-------------|--------|-------|
| repo/docs/product/service/subsystem | `README.md` | updated / justified / missing | canonical artifacts linked? |

## Cost Budget Status
| Scope | Status | Notes |
|-------|--------|-------|
| AI/model budget | not applicable / within budget / warning / approval required / missing | model escalation, retries, fan-out, tool-call breadth, and recurring usage checked? |
| Telemetry rollup | not applicable / current / stale / missing | required only when thresholds are enforceable |
| Cost architecture | not applicable / current / stale / missing | workload classes, cache, batch, routing maturity, cascades checked? |
| Router eval | not applicable / current / stale / missing | required for L5/L6 routing or cascades |

## External Skill Security Status
| Skill | Status | Notes |
|-------|--------|-------|
| name / n/a | not applicable / approved / rejected / missing trust record / scan required / signature required | source pinned? SkillSpector/equivalent scan? critical/high findings triaged? install scope approved? |
---

## Artifact B: tasks.md patch

For each P0 and P1 finding without an existing task: add task entry (match existing style).
Note: finding ID → task ID mapping.

## Artifact C: CODEX_PROMPT.md patch

Make two targeted edits:

**1. Fix Queue** — insert/replace the `── Fix Queue ──` section (between SESSION HANDOFF and Phase queue).
List every P0 and P1 finding as a concrete actionable task for Codex.
Format:
```
─── Fix Queue (resolve before Phase N queue) ────────────────────────
🔴 FIX-N [P0] — Short title
  File: src/foo.py:line · Change: one-line description · Test: what to verify

🟡 FIX-N [P1] — Short title
  File: src/bar.py:line · Change: one-line description · Test: what to verify
```
If no P0/P1 findings: write `─── Fix Queue ─── (empty — proceed to phase queue)`.

**2. Open Findings** — update the findings table:
- Close verified findings (Closed + evidence)
- Add new P2/P3 from this cycle
- Update baseline and "Next task" line
- Bump version (v3.N → v3.N+1)
- If runtime verification failed or was missing for a required task, add a Fix
  Queue item instead of marking the task complete.
- If a changed boundary lacks a README-first index update or justified
  omission, add a P1/P2 finding depending on blast radius.
- If AI/model cost changed, update `## Cost Budget State` in CODEX_PROMPT.md
  and add a Fix Queue item for missing budget/approval evidence.
- If external skills changed, add/update a Fix Queue item for missing trust
  record, missing scan/signature/hash evidence, untriaged CRITICAL/HIGH
  findings, or unapproved global install.

Do NOT touch: IMPLEMENTATION CONTRACT, MANDATORY PRE-TASK PROTOCOL, FORBIDDEN ACTIONS, GOVERNING DOCUMENTS.

## Closing rule

A finding is Closed only when:
1. You verified the fix in code (file:line exists)
2. A test exists that would fail without the fix
Self-closing without code verification is forbidden.

## Report

When done, output:
Cycle N complete.
- REVIEW_REPORT.md: N findings (P0: X, P1: Y, P2: Z)
- tasks.md: N tasks added
- CODEX_PROMPT.md: bumped to vX.Y, baseline updated
- Cost budget: OK / warning / approval required / missing
- Stop-ship: Yes/No

Next: move REVIEW_REPORT.md to archive/PHASE{N}_REVIEW.md before Cycle N+1.
```
