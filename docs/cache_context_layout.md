# Cache Context Layout

## Purpose

Prompt caching is a prompt architecture concern. It only saves cost and latency
when reusable prompt prefixes stay byte-stable across requests.

Anthropic's prompt caching documentation states that caching resumes from
specific prompt prefixes and that the cached prefix includes `tools`, `system`,
and `messages` in order up to the selected cache breakpoint. It recommends
placing static content at the beginning and marking the end of reusable content.
Source: https://platform.claude.com/docs/en/build-with-claude/prompt-caching

This playbook treats that as a design rule: cacheable context must be separated
from volatile task context.

## Stable Prefix

Put long-lived, reused material here:

- system policy
- role contract
- repo/task invariants
- tool schemas
- canonical project context
- long-lived retrieved docs
- stable examples
- stable output schemas

Allowed changes are intentional architecture or contract changes. If this area
changes every run, prompt caching will not deliver predictable savings.

## Volatile Suffix

Put per-run or frequently changing material here:

- current user message
- timestamp/current date
- run ID/request ID/random ID
- current diff
- latest test output
- temporary diagnostics
- one-off tool results
- transient task notes
- short-lived retrieval snippets

## Hard Rules

- Do not put timestamps, run IDs, random IDs, current date, current diff, latest
  test output, or temporary diagnostics in the stable prefix.
- Do not reorder tool schemas casually; schema order can affect prefix
  stability.
- Do not combine stable policy and volatile state into one monolithic prompt
  string when using provider prompt caching.
- Do not claim cache savings without cache-hit telemetry or provider/gateway
  usage data.
- If cache layout changes, update cost architecture and rerun relevant evals.

## Layout Template

```yaml
cache_context_layout:
  stable_prefix:
    - system policy
    - role contract
    - tool schemas
    - canonical project context
  cache_breakpoint:
    provider: anthropic | openai | gateway | n/a
    location: "after stable prefix"
    ttl: "5m | 1h | provider_default | n/a"
  volatile_suffix:
    - current user message
    - current diff
    - latest test output
  prohibited_in_prefix:
    - timestamp
    - run_id
    - random_id
    - transient diagnostics
  telemetry:
    cache_hit_metric:
    cache_write_metric:
    cache_read_metric:
    target_hit_rate:
```

## Review Check

Reviewer should flag:

- volatile fields above the cache boundary
- cache-required workloads with no cache-hit telemetry
- dynamic router changes that lower cache hit rate beyond the declared threshold
- broad context packet insertion before the cache boundary
- prompt template changes that reorder stable blocks without an eval or cost
  reason
