# Test-First Implementation Protocol

Status: documented governance protocol
Empirical status: project outcome improvement is not established; first paired
pilot did not support an improvement claim

## Purpose And Boundary

This protocol defines the inner implementation loop for work that benefits from
a public executable specification. It makes test-first behavior explicit while
preserving the Playbook's Lean-Core / Standard / Strict proportionality.

The protocol adds no server, database, UI, test runner, or always-on agent
runtime. Projects use the test tools already appropriate to their stack.

A public executable spec guides the implementer and produces reviewable command
evidence. It is not final proof of correctness, release readiness, security, or
project benefit. Required CI, capability evaluation, runtime verification,
review, and human approval remain separate gates.

## Applicability Decision

Classify the task before implementation as `required`, `optional`, or
`not_applicable`. Change semantics take precedence over the apparent file type:
a configuration change that changes behavior is not docs-only work.

The task schema now carries deterministic routing inputs. Keep a concrete
`Test`, `Verification`, or acceptance-criterion verifier in every task;
`not_applicable` never means no verification.

| Decision | Use when | Minimum action |
|----------|----------|----------------|
| `required` | A reproducible defect is fixed; observable executable behavior is added or changed in Standard/Strict; or a security, compliance, data-integrity, side-effect, state-transition, retry/termination, retrieval, or routing boundary changes in any mode | Demonstrate the smallest useful public spec failing for the intended reason before implementation, then make it pass |
| `optional` | Lean-Core work changes low-risk behavior and a concrete verifier is proportionate; a behavior-preserving refactor is already bounded by relevant tests; or short-lived characterization is needed before the final task contract is known | Prefer a focused spec when it reduces ambiguity; otherwise record the rationale and run the declared verifier before and after |
| `not_applicable` | The change is prose-only documentation, navigation, comments, formatting, evidence indexing, or metadata with no executable semantics | Run the relevant deterministic validator, link checker, diff check, or bounded manual verification |

If a task starts as optional or not applicable and reveals a semantic or higher-
risk change, stop and reclassify it before continuing.

## Deterministic Risk Routing

The validator materializes these canonical fields for every task record:

| Field | Values | Meaning |
|-------|--------|---------|
| `risk_level` | `low`, `medium`, `high`, `critical` | Task-local blast radius and reversibility; separate from adoption mode |
| `public_tests_required` | `not_required`, `conditional`, `required` | Whether RED/GREEN public executable specs gate implementation |
| `critic_required` | `not_required`, `conditional`, `required` | Whether an independent evidence/oracle audit is required |
| `holdout_required` | `not_required`, `conditional`, `required` | Whether restricted acceptance evidence is required |
| `mutation_required` | `not_required`, `conditional`, `required` | Whether mutation evidence is required for the affected logic |
| `property_required` | `not_required`, `conditional`, `required` | Whether invariant/property evidence is required |
| `visual_contract` | `not_applicable`, `optional`, `required` | Whether visual evidence applies and whether it gates completion |

Missing historical metadata resolves to `medium` risk, `conditional` test gates,
and an `optional` visual contract. This preserves validity without treating
unknown risk as an approved low-risk waiver. New task templates set explicit
lighter values where Lean-Core work is known to be low risk.

Resolve each gate in this order:

1. Validate the task record. Unknown enum values are blockers.
2. Apply the risk-tier floor below.
3. Treat an explicit `required` value as required even when the floor is lower.
4. Resolve `conditional` using the applicability predicates below.
5. Accept `not_required` only when it does not contradict a risk-tier floor or
   an applicability predicate that says required. Record the rationale for
   high/critical tasks.
6. If task metadata conflicts with the floor, emit `TEST_GOVERNANCE_GAP` and
   stop for a corrected task record or human-approved risk decision. Do not
   silently downgrade the gate.

### Risk-Tier Floors

| Risk | Public tests | Test critic | Holdout | Mutation / property | Visual | Approval and evidence |
|------|--------------|-------------|---------|---------------------|--------|-----------------------|
| `low` | Required for reproducible defects; otherwise conditional for executable semantics | Not required unless explicit | Not required unless explicit | Not required unless explicit | Use declared contract; non-UI is not applicable | Normal task evidence and mode-appropriate human boundary |
| `medium` | Required for executable semantic changes; concrete verifier allowed for non-semantic work | Conditional when an acceptance criterion lacks a complete deterministic oracle or crosses a material interface | Not required unless explicit | Conditional only when an applicability predicate below matches | Use declared contract; required stays blocking | Phase-boundary approval plus acceptance-criterion evidence mapping |
| `high` | Required for executable semantic changes and applicable failure paths | Required | Conditional; required when restricted acceptance is feasible and public-test overfitting or contamination is material | Apply each matching predicate; at least one stronger oracle is required for critical executable logic when feasible | Required for user-facing UI changes; otherwise not applicable | Explicit evidence mapping and human approval are required |
| `critical` | Required for executable semantics, negative paths, and failure handling | Required | Required when a restricted executable acceptance oracle is feasible; otherwise human-approved exception | Each matching predicate is required; an unavailable tool needs documented alternative evidence and approval | Required for user-facing UI changes; otherwise not applicable | Missing required evidence is stop-ship; explicit human approval is required |

### Applicability Predicates

Use these predicates rather than model confidence:

- Public tests apply when executable behavior changes or a reproducible defect is
  fixed. Prose-only work uses a concrete verifier.
- A critic applies when required by the risk floor or when acceptance evidence
  has an unresolved oracle gap. The critic remains an evidence auditor, not
  merge authority.
- Holdout evidence applies when implementer-visible tests create a material
  overfitting/contamination risk and a restricted acceptance suite is feasible.
- Mutation evidence applies when branch, calculation, authorization, retry, or
  state-transition correctness depends on tests detecting deliberately wrong
  behavior and a stable stack tool exists.
- Property evidence applies when stable invariants span a large input/state
  space, including parsers, schemas, state machines, routing, retrieval
  semantics, or termination logic.
- A visual contract applies only when rendered layout, appearance, or visual
  fidelity is part of acceptance. Behavior-only or non-UI work may mark it not
  applicable.

Property and mutation are independent supplements; either or both may apply.
Use `docs/testing/property_and_mutation_oracles.md` to resolve their predicates,
scope deterministic targets, and avoid treating coverage or a universal mutation
score as oracle evidence.

Cross-vendor or cross-model review may be selected for high/critical work, but
it is not a default gate. Independent context, structured evidence, and the
required deterministic checks are the baseline.

If a resolved required gate has no implemented protocol, command, owner, or
evidence destination, complete that prerequisite first or block the task. Never
silently downgrade the field or claim that an unavailable gate ran.

## Adoption Mode Minimums

Adoption mode sets the minimum. Task risk may strengthen it; task risk does not
make every low-risk change inherit the full Strict control surface.

| Mode | Test-first minimum | Broader evidence |
|------|--------------------|------------------|
| Lean-Core | Focused RED/GREEN is optional for routine low-risk work and required for reproducible defects or high-risk semantics. A concrete local test or verification command is always required. | Relevant checks before and after; shortened runtime verification for risky edits or correction turns |
| Standard | Public executable specs are required for practical automated changes to behavior and reproducible defect fixes. Changed boundaries receive the relevant integration or contract check. | Targeted spec, declared suite, CI, and runtime verification at risky edits or phase boundaries |
| Strict | Public executable specs are required for executable semantic changes. High-risk work also covers applicable negative and failure paths. Truly non-semantic work may still be not applicable. | Full relevant CI/eval/review gates, durable command evidence, and runtime verification for privileged or risky writes |

All modes retain explicit acceptance criteria, bounded correction, evidence
before completion, no self-review, and human approval at meaningful risk
boundaries.

A high/critical task in a Lean-Core project receives the task-local risk floor;
it does not automatically make every other task Strict. Repeated high-risk work
is a signal to reconsider the project mode and maintained evidence surface.

## Public Executable Specs

A public executable spec is visible to the implementer and has a deterministic
runner or assertion. Valid forms include:

- a unit test for local behavior
- an integration test for a changed component boundary
- a contract or schema test for an interface
- a property check for an invariant
- a fixture paired with a deterministic runner and assertions
- a CLI smoke check with explicit exit-code and output expectations
- a UI behavior test for an observable interaction

For probabilistic AI behavior, public tests should cover deterministic
invariants and fixtures. Dataset quality, thresholds, judge behavior, and
product claims remain governed by
`docs/evaluation/EVAL_FIRST_DEVELOPMENT.md` and the applicable capability eval.

The following are not executable specs by themselves:

- prose acceptance criteria
- a fixture without a runner or assertions
- a screenshot without a comparison rule
- a critic verdict
- code inspection or an agent statement that the change works

## RED -> GREEN -> REFACTOR

### 1. Establish Scope And Baseline

Read the task acceptance criteria and relevant existing tests. Select the
smallest executable spec that proves the intended behavior. Run the relevant
pre-change checks and record unrelated existing failures separately.

### 2. RED

Add or update the focused public spec, then run it before implementation. The
failure must be caused by the missing or incorrect target behavior, not by a
syntax error, missing dependency, broken environment, or unrelated baseline
failure.

For a defect fix, an existing test that already reproduces the defect may serve
as RED when its failing output is captured. If a new test passes immediately,
do not manufacture a failure: determine whether the behavior already exists or
the oracle is too weak, then update the task or test accordingly.

An intentional, expected RED result is specification evidence. It is not a
failed correction turn.

### 3. GREEN

Implement only enough behavior to satisfy the focused spec and acceptance
criterion. Rerun the focused command. Do not weaken assertions, remove coverage,
or reinterpret the acceptance criterion to obtain a green result.

### 4. REFACTOR

Improve the implementation only while the focused spec remains green. Keep
refactoring inside the declared file and behavior scope.

### 5. Broaden Verification

Run the task's declared suite, lint/type/schema/contract checks, relevant
capability eval, and CI or project verifier as required by the selected mode.
Compare the result with the recorded baseline. Public-spec success does not
waive a failing broader gate.

## Evidence Record

Record enough evidence for another reviewer to reproduce the claim:

| Evidence | Required content |
|----------|------------------|
| Applicability | `required`, `optional`, or `not_applicable`, plus rationale when not required |
| Baseline | Exact relevant command, exit status, and pre-existing failures |
| RED | Exact focused command and expected failure signal when test-first is required |
| GREEN | Exact focused command and passing result or artifact path |
| Broader verification | Declared task/CI/eval commands, results, and unresolved failures |
| Stronger oracles | Resolved decision, target scope, command/config, pre-run threshold or rationale, result/receipt, and approved exception when required |
| Repository state | Changed-file list or diff evidence showing the claimed change exists |
| Exception or accepted risk | Owner, reason, scope, expiry or follow-up task, and human approval when required |

For routine Lean-Core work, command output plus `git diff` and the changed-file
list can be sufficient. For risky writes, correction turns, or tasks whose
runtime-verification field requires it, follow
`docs/runtime_verification_protocol.md`. `tools/receipt_run.py` may capture
stdout/stderr, hashes, exit code, Git state, and environment state.

A receipt is a factual evidence envelope. It does not assign `passed`,
`verified`, `release_ready`, or merge authority.

## Independent Test Critic

Run the Test Critic when the resolved `critic_required` route requires it, or as
an optional scoped audit when a human reviewer requests it. Routine low-risk
Lean-Core work does not require a critic report by default. Use
`prompts/audit/PROMPT_TEST_CRITIC.md` in a fresh review context that is separate
from the implementer's private reasoning; another vendor is optional.

Supply the canonical task and acceptance criteria, declared and resolved route,
diff scope, public-test and broader command results, receipts, known baseline
failures, applicable stronger-oracle summaries, and exception/approval records.
Restricted holdout cases stay hidden; only their result evidence enters the
audit.

The critic maps acceptance criteria to evidence and checks oracle sensitivity,
missing applicable cases, public-test overfitting, flaky signals, and evidence
traceability. It uses four dispositions:

| Disposition | Treatment |
|-------------|-----------|
| `BLOCKER` | Allowed only for a cited deterministic failure, missing resolved-required evidence, or an explicit stop-ship policy |
| `CONCERN` | Advisory scoped gap without deterministic blocking authority |
| `ACCEPTED_RISK` | Existing human-approved exception; the critic cannot grant one |
| `NO_FINDING` | No issue found in the named reviewed scope; not proof of correctness or completion |

The critic does not assign merge readiness or P-level severity, rewrite code,
perform broad style/architecture review, or turn model confidence into a gate.
Consolidated review validates its evidence and assigns any P-level finding.
The first paired pilot did not support a test-first improvement claim. Until a
larger preregistered pilot and calibration evidence support one, no critic result
or public-test outcome supports an empirical quality or productivity claim.

## Failure And Escalation

Use `docs/bounded_correction_turns.md` for correction limits and stop conditions.
Escalate instead of silently changing the task when:

- the intended behavior cannot be expressed as a reliable public spec
- requirements are ambiguous or conflict with the existing contract
- the baseline is already red in the affected area
- the focused test is flaky or depends on uncontrolled external state
- a public test would disclose restricted holdout data or sensitive values
- the implementation requires files, budget, or runtime outside task scope
- the same unexpected failure repeats or the correction budget is exhausted

Do not delete or weaken a failing test, acceptance criterion, security boundary,
or project verifier as a repair strategy. Record an approved exception or mark
the task blocked.

## Completion And Claims

Completion requires the declared deterministic gates and evidence, not an
implementer's prose summary. It is valid to report exact observations such as a
command exit code, test count, expected RED signal, or receipt path.

Public-test evidence alone does not justify claims that the change is correct,
safe, release-ready, empirically validated, or that this protocol improves
quality, reliability, repair time, or productivity. Those claims require the
applicable independent evidence and, for workflow improvement, a recorded paired
pilot with a supportive adjudicated outcome.

## Related Protocols

- `docs/adoption_modes.md` - mode-specific artifact and evidence floors
- `docs/evaluation/EVAL_FIRST_DEVELOPMENT.md` - stochastic capability and product evaluation
- `docs/runtime_verification_protocol.md` - intent-to-filesystem verification for risky writes
- `docs/bounded_correction_turns.md` - repair limits and escalation
- `docs/heavy_task_mode.md` - selective proof-first additions for unusually risky work
- `docs/evaluation/CI_EVAL_GATE.md` - CI treatment of capability evaluation
- `docs/testing/property_and_mutation_oracles.md` - routed property and mutation oracle selection/evidence
