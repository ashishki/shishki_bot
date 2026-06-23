# Cost Budget Guardrails

## Purpose

LLM and agent cost is an architecture constraint. It must be tracked, attributed,
budgeted, and gated like latency, security, and reliability.

This policy applies when a project uses LLM calls, agent loops, dynamic
workflows, tool-using agents, retrieval, evaluators, or multi-agent review.

## Default Posture

- Prefer deterministic code before an LLM call.
- Prefer the smallest sufficient model for each workload.
- Track cost per run, task, feature, agent, user/operator, and project.
- Budget before enabling fan-out, retry loops, dynamic workflows, or persistent
  agents.
- Require approval before a run crosses a declared cost threshold.

## Required Budget Artifact

Use `templates/COST_BUDGET.md` when any of these are true:

- the project has an active AI capability profile
- model usage is expected to be recurring
- a workflow can spawn multiple agents or retries
- the system serves multiple users, tenants, or operators
- LLM cost is a material project constraint

Lean projects may keep the budget inline in `docs/CODEX_PROMPT.md` or
`docs/CONTRACT_LITE.md`. Standard/Strict projects should keep a dedicated
`docs/COST_BUDGET.md`.

## Required Cost Architecture Artifact

Use `templates/COST_ARCHITECTURE.md` to create
`docs/ai_cost_architecture.md` when any of these are true:

- AI/model usage is recurring or materially costly
- the project uses agent loops, dynamic workflows, or multi-agent review
- the project declares enforceable cost thresholds
- prompt caching, batch execution, dynamic routing, or cascades are part of the
  cost-control strategy
- Strict mode is selected and AI/model work is active

Lean projects may keep this inline when AI usage is one-off and low-risk. Do
not create placeholder cost architecture files only to satisfy a checklist.

## Minimum Telemetry Automation

Use `docs/cost_telemetry_protocol.md` when AI/model usage is recurring,
agentic, dynamic-workflow based, multi-agent-review based, or materially costly.

Minimum artifact:

- `docs/ai_cost_telemetry.jsonl` — one JSON object per call/run
- `schemas/cost_telemetry_entry.schema.json` — entry contract
- `reports/ai_cost_rollup.md` — generated rollup report

Minimum command:

```bash
python3 tools/cost_rollup.py \
  --input docs/ai_cost_telemetry.jsonl \
  --output reports/ai_cost_rollup.md \
  --strict
```

Use `--max-total-cost` and `--max-run-cost` in CI when thresholds are declared
in `docs/COST_BUDGET.md`.

## Minimum Tracking Fields

Every LLM call or agent run should be attributable to:

- project
- task or workflow
- agent/role
- model
- user/operator or service account
- feature/workload
- environment

Track at least:

- input tokens
- output tokens
- total tokens
- estimated cost
- latency
- retry count
- tool call count
- eval or quality result when available

## Budget Gates

| Gate | Lean | Standard | Strict |
|------|------|----------|--------|
| Per-run budget | Required for AI tasks | Required | Required |
| Per-agent/workflow budget | Optional | Required for agent/workflow tasks | Required |
| Per-user/tenant budget | Optional | Required for multi-user systems | Required |
| Monthly project budget | Required if recurring AI use | Required | Required |
| Approval before budget overrun | Required | Required | Required |
| Hard kill switch | Optional | Required for agent loops | Required |

## Guardrails

Use explicit limits for:

- max model calls per run
- max tool calls per run
- max retries per failing call
- max parallel agents
- max context packet or file-read breadth
- max spend per run/task/day/month
- max time before human review

Stop or request approval when:

- the run is projected to exceed budget
- a retry loop repeats the same failure class
- tool calls are not adding new evidence
- model escalation would materially increase cost
- a dynamic workflow wants to increase fan-out beyond the declared cap

## Cost Reduction Rules

- Use deterministic prefilters before LLM review.
- Route easy subtasks to cheaper models only after eval shows quality holds.
- Compare cost per successful task, not only cost per call.
- Use the full cost equation from `templates/COST_BUDGET.md`; failed cheap
  attempts, verifier calls, retries, tools, and human rework are part of cost.
- Track retries and rework; a cheap model that fails more often may be more
  expensive end-to-end.
- Avoid sending full histories or broad file contexts when scoped retrieval is
  enough.
- Cache stable context and reuse deterministic indexes where safe.
- Keep stable prompt/cache prefixes separate from volatile task suffixes. See
  `docs/cache_context_layout.md`.
- Apply output-token and reasoning/effort caps before adopting dynamic routing.
- Use dynamic workflows only when executable orchestration reduces waste or risk
  enough to justify the extra agent calls.
- Use dynamic routers only after cheaper controls are implemented and
  `docs/router_eval.md` proves cost reduction without quality/latency regressions.

## Cascade Rules

A cascade is allowed only when:

- the escalation judge is independent from the cheap model, or the cheap
  model's confidence is calibrated on the project eval set
- the escalation threshold comes from a measured cost/quality curve
- failed cheap attempts are included in `cost_per_successful_task`
- verifier cost is included in `cost_per_successful_task`
- the workload's risk level permits the observed false-negative rate

Cheap self-judgment is not enough for high-risk or correctness-sensitive work.

## Review Requirements

Reviewer prompts and workflow policies should flag:

- missing budget artifact for an active AI capability
- material model escalation without architecture update
- missing per-run/per-agent budget for agent loops
- unbounded retries, fan-out, or tool calls
- cost-saving change without eval/latency comparison
- cost architecture missing for recurring/material AI work
- cache-required workload with no cache-hit telemetry or unstable prefix layout
- dynamic router or cascade without `docs/router_eval.md`
- cost regressions not reflected in `docs/CODEX_PROMPT.md` or
  `docs/COST_BUDGET.md`

## Evidence Sources

See `reference/cost_guardrails_research.md` for current external evidence and
tool references.
