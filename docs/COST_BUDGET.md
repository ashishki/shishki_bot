# Cost Budget

Mode: Standard
Owner: human
Last updated: 2026-06-23

## Budget Scope

| Scope | Limit | Window | Enforcement |
|-------|-------|--------|-------------|
| Per task / run | To be filled in `docs/PROJECT_BRIEF.md` | Task | Approval before overrun |
| Per user / operator | Not applicable yet | Not applicable | Approval before introducing attribution |
| Per project / month | Minimal fixed hosting/database cost; exact ceiling to confirm before deployment | Month | Approval before recurring AI usage or paid infrastructure increase |
| Per agent / workflow | Not applicable yet | Not applicable | Approval before adding agent workflows |

## Attribution Tags

Every LLM call or agent run should be attributable to:

- project
- task or workflow
- agent/role
- model
- user/operator or service account
- feature/workload
- environment

## Model Routing Budget

| Workload | Default model/class | Escalation allowed when | Cheaper fallback | Verification metric |
|----------|---------------------|--------------------------|------------------|---------------------|
| Repository setup and docs | Minimum sufficient model | Required context is ambiguous or review risk increases | Deterministic scripts and direct file edits | `python3 tools/integrity_check.py --root .` exits 0 |
| Production bot behavior | No model | Not applicable in v1 | Deterministic application logic | Tests pass |

## Cost Equation

Optimize cost per successful task, not cost per model call.

```text
cost_per_successful_task =
  (fresh_input_cost
 + cached_input_cost
 + output_cost
 + tool_cost
 + retry_cost
 + verifier_cost
 + human_rework_cost_estimate)
 / successful_completion_rate
```

| Component | Measurement Source | Included? | Notes |
|-----------|--------------------|-----------|-------|
| fresh_input_cost | telemetry/provider/gateway | yes/no | |
| cached_input_cost | telemetry/provider/gateway | yes/no | |
| output_cost | telemetry/provider/gateway | yes/no | |
| tool_cost | traces/manual estimate | yes/no | |
| retry_cost | telemetry/rollup | yes/no | |
| verifier_cost | telemetry/rollup | yes/no | |
| human_rework_cost_estimate | review/ops estimate | yes/no | |
| successful_completion_rate | eval/review outcome | yes/no | |

## Guardrails

- Max model calls per run: not set until brief is filled
- Max tool calls per run: keep bounded to the active task
- Max retries per failing call: 1 without new evidence
- Max parallel agents: 0 unless explicitly approved
- Max output tokens per workload: use concise task outputs
- Max reasoning/effort level per workload: minimum sufficient for task risk
- Target cache hit rate: not applicable yet
- Max escalation rate: ask before material model escalation
- Stop condition for repeated equivalent failures: stop after two equivalent failed attempts without new evidence
- Human approval threshold: any recurring/material AI usage, budget overrun, or external side effect

## Required Measurements

- input tokens
- output tokens
- total tokens
- estimated cost
- latency
- retry count
- tool call count
- result quality/eval outcome where available

## Telemetry

- Telemetry file: `docs/ai_cost_telemetry.jsonl`
- Entry schema: `schemas/cost_telemetry_entry.schema.json`
- Rollup command:

```bash
python3 tools/cost_rollup.py \
  --input docs/ai_cost_telemetry.jsonl \
  --output reports/ai_cost_rollup.md \
  --strict
```

- CI threshold command:

```bash
python3 tools/cost_rollup.py --strict --require-file --max-total-cost 25 --max-run-cost 2
```

## Review Rule

A cost-saving change is acceptable only when quality and latency stay within the
declared thresholds. A cheaper route that causes retries, rework, or lower pass
rate is not a real saving.
