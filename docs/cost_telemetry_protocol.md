# Cost Telemetry Protocol

## Purpose

This is the provider-agnostic minimum telemetry layer for AI/model cost. It does
not replace Braintrust, Maxim, TrueFoundry, OpenTelemetry, or provider billing
APIs. It gives every playbook project a small, CI-friendly artifact contract
before a full observability stack exists.

## Telemetry File

Default path:

```text
docs/ai_cost_telemetry.jsonl
```

Each line is one JSON object matching
`schemas/cost_telemetry_entry.schema.json`. Use
`templates/COST_TELEMETRY_ENTRY.json` as the entry template.

## Required Fields

Every entry must include:

- timestamp
- project
- run_id
- source
- provider
- model
- agent_role
- environment
- input_tokens
- output_tokens
- total_tokens
- estimated_cost_usd

Recommended attribution fields:

- task
- workflow
- user_or_operator
- feature
- workload_class
- routing_maturity_level
- retry_count
- tool_call_count
- latency_ms
- cache_hit
- cache_read_tokens
- cache_write_tokens
- router_decision
- escalation_reason
- quality_result

## Source Priority

Use the most authoritative available source:

1. Provider usage object or billing/usage API.
2. Gateway or tracing span that records provider-returned usage.
3. SDK usage object.
4. Manual estimate, clearly marked as `source: manual_estimate`.

Do not bill customers or make irreversible financial decisions from client-side
estimates alone. Use estimates for guardrails, trend detection, and review
evidence until authoritative billing data is wired.

## How Projects Build This

Downstream projects build telemetry at the application LLM boundary, not by
depending on this playbook to monkey-patch every provider SDK.

Required pattern when thresholds are enforceable:

1. Create one project-owned provider boundary, for example `app/ai/client.py`,
   `app/ai/telemetry.py`, or the equivalent TypeScript module.
2. Route all OpenAI, Anthropic, gateway, agent SDK, or workflow runtime calls
   through that boundary.
3. Extract usage from the provider/gateway/SDK response when available.
4. Map usage into `schemas/cost_telemetry_entry.schema.json`.
5. Write one JSONL entry to `docs/ai_cost_telemetry.jsonl` in local/test
   workflows, or export the same JSON shape to the selected gateway/tracing
   backend in production.
6. Run `tools/cost_rollup.py` in review/CI using thresholds from
   `docs/COST_BUDGET.md`.

When `docs/ai_cost_architecture.md` declares prompt caching, dynamic routing,
or cascades, telemetry should also expose cache-hit data, router decisions,
escalation reasons, and workload class so reviewers can evaluate cost per
successful task instead of cost per isolated call.

Use `templates/COST_TELEMETRY_ADAPTER.md` to create the implementation task.

This keeps the playbook provider-neutral while still giving each project a
buildable path. The v2 provider SDK adapters would only automate step 3-5 for
common SDKs; they are not required for the architecture to work.

## Rollup Tool

Run:

```bash
python3 tools/cost_rollup.py \
  --input docs/ai_cost_telemetry.jsonl \
  --output reports/ai_cost_rollup.md \
  --strict
```

Optional gates:

```bash
python3 tools/cost_rollup.py \
  --input docs/ai_cost_telemetry.jsonl \
  --output reports/ai_cost_rollup.md \
  --strict \
  --require-file \
  --max-total-cost 25 \
  --max-run-cost 2
```

The report rolls up cost by run, task, model, and agent role. It fails when
strict validation or configured thresholds fail.

## When Required

Use telemetry rollup when:

- AI/model usage is recurring
- agent loops or dynamic workflows are active
- multi-agent review cost is material
- Strict mode is selected
- a task changes model routing, retry/fan-out limits, or tool-call breadth
- a cost-saving change claims lower cost
- `docs/ai_cost_architecture.md` declares cache-hit, routing, cascade, or
  escalation thresholds

Lean projects may skip persistent telemetry for one-off tasks, but must still
record the budget boundary and any budget issue in `docs/CODEX_PROMPT.md`,
`AGENTS.md`, or the task result.

## CI Integration

Use this as a cheap CI gate before adopting a vendor platform:

```yaml
- name: AI cost telemetry rollup
  run: python3 tools/cost_rollup.py --strict --require-file --max-total-cost 25
```

Set thresholds from `docs/COST_BUDGET.md`.

## Adapter Template

Downstream projects can start from:

```text
templates/cost_adapters/python/telemetry_adapter.py
```

The adapter is provider-neutral. It extracts common OpenAI/Anthropic/gateway
usage fields from dict-like or object-like responses and writes entries in the
playbook JSONL shape. Projects still own pricing, budget approval, and the
provider boundary.

## Known Limits

- The rollup tool does not automatically intercept provider SDK calls.
- `templates/cost_adapters/python/telemetry_adapter.py` provides a project-owned
  adapter template, not zero-config monkey-patching of provider SDKs.
- Pricing tables are not embedded; projects should log `estimated_cost_usd`
  from the gateway/provider/tooling they trust.
- Provider-specific SDK wrappers can be added inside downstream projects when
  their runtime/provider layer is known.
