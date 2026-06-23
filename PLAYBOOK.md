# AI Workflow Playbook

Version: 1.2
Last updated: 2026-05-26

---

## 1. Philosophy

### AI-Assisted Development

The developer is the architect and reviewer. AI agents (Codex) write code. Review agents validate it. The human approves phase gates. Nothing progresses without human sign-off.

This is not "AI writes everything." This is "AI does the mechanical work under a structure you control." The value of this workflow is the structure — the prompts, the contracts, the review cycle — not the raw capability of any individual agent call.

### The Three-Layer Loop

```
Strategist (architecture)
    → Orchestrator (phase execution)
        → Codex agents (implementation, one task at a time)
            → Review cycle (META → ARCH → CODE → CONSOLIDATED)
                → Human approval
                    → next phase
```

Every layer has a defined input, a defined output, and a defined boundary with the next layer. No layer crosses into another layer's responsibility.

### The Four-Layer Interpretation

The repository is easiest to evolve safely if you interpret it through four logical layers:

1. **Policy / Governance** — phases, contracts, review policy, stop conditions, immutable rules
2. **Proof / Evidence** — explicit evidence collection, evaluation artifacts, selective proof-first handling for risky work
3. **Optional Execution Patterns** — parallel subagents, isolated worktrees, fanout/merge, runtime selection
4. **Harness / Packaging** — hooks, Claude Code settings, bootstrap, templates, install story

This interpretation does not replace the operational layer map below. It clarifies what the playbook is optimizing for: governance first, execution substrate second.

### Why This Works

- **Phase gates** prevent drift. A flaw caught at the end of Phase 2 is infinitely cheaper than one discovered in Phase 8.
- **Subagents** prevent context collapse. Each task and each review runs in its own context window with exactly the files it needs.
- **CODEX_PROMPT.md** is the single source of truth for session state. Any agent can resume a session by reading it. Nothing is held in conversational memory.
- **IMPLEMENTATION_CONTRACT.md** is the unchanging floor. Architectural decisions may evolve; the contract does not, without an explicit ADR.
- **Right-sizing comes first.** Solution shape, capability profiles, governance intensity, and runtime tier are separate decisions. None should be escalated without justification.

### Continuity Model

The playbook does not use fuzzy agent memory as authority. It uses explicit files with different roles:

- **Canonical truth:** `ARCHITECTURE.md`, `IMPLEMENTATION_CONTRACT.md`, `tasks.md`, `CODEX_PROMPT.md`, ADRs, audit reports, evaluation artifacts, code, tests
- **Retrieval convenience:** `DECISION_LOG.md`, `IMPLEMENTATION_JOURNAL.md`, `EVIDENCE_INDEX.md`, task-level `Context-Refs`
- **Role-scoped recall:** the Strategist, Orchestrator, implementer, and reviewers read only the continuity artifacts relevant to the current task or finding

Retrieval is mandatory when a task changes architecture, runtime, risky boundaries, open findings, or capability semantics. Otherwise, keep reads narrow.

### Filesystem Reality and Runtime Verification

The playbook treats model output as intent until repo state proves otherwise.
The filesystem, git diff, tests, CI, eval artifacts, and canonical docs outrank
agent claims, generated context packets, and chat memory.

For risky writes, command-surface changes, heavy tasks, provider/tool changes,
and correction turns, the implementer or orchestrator must capture a lightweight
runtime verification record:

- declared operation and claimed files
- before state where useful: git commit, file existence, SHA-256 hash
- after state: changed files, diff evidence, file existence, SHA-256 hash
- tests/evals actually run
- verification status and failures

No task is complete merely because an agent says it is complete. Completion
requires evidence that the claimed files, tests, and state updates exist. See
`docs/filesystem_reality_principle.md` and
`docs/runtime_verification_protocol.md`.

Correction loops are bounded. Default maximum: two implementation correction
turns and two test-healing turns unless the task explicitly enables heavy mode.
Repeated failures, unchanged test output, increased failure count, budget
exhaustion, or out-of-scope edits escalate to the Orchestrator or human. See
`docs/bounded_correction_turns.md`.

### Cognition Layer

The cognition layer extends continuity across long-lived projects and cross-project portfolios without changing the authority model:

- repo files remain source of truth
- Obsidian is an optional markdown UI and graph browser, not infrastructure
- generated retrieval manifests and context packets are convenience artifacts
- deterministic retrieval is preferred over semantic retrieval
- semantic/vector search, if used, only proposes cited candidates
- agents consume bounded role-specific packets rather than vault dumps

The minimum project-local cognition artifact is `docs/COGNITION_MANIFEST.md`, which maps canonical truth, eval memory, decision lineage, evidence surfaces, and packet scopes. The minimum generated artifact is `generated/cognition/index.json`, produced by `tools/cognition_index.py` when automation is useful.

Use the cognition docs when a project has multiple phases, recurring findings, active evals, ADR lineage, or cross-project reuse:

- `docs/cognition/architecture.md`
- `docs/cognition/retrieval_context_packets.md`
- `docs/cognition/git_integration.md`
- `docs/cognition/obsidian_vault_architecture.md`

### Prompt Context Policy

This playbook treats prompt design as an execution concern, not just a documentation concern. A good implementation prompt is a compressed, task-ready digest of the relevant context, not a list of files for the model to discover and summarize itself.

Default rule: prefer `inline digest` over `read these docs`.

- inline only the facts that change implementation behavior: applicable contract rules, task dependencies, concrete prior artifacts, narrow architectural constraints, and the immediate pipeline / flow
- keep full-document reads for architecture-shaping, security-sensitive, ambiguous, or review-heavy tasks where compression would hide important tradeoffs
- if a large document contributes only a few actionable facts, put those facts directly in the prompt instead of linking the document
- task prompts should usually contain the minimum executable context needed to start coding without opening multiple additional files

Prompt anti-patterns:

- "Read `ARCHITECTURE.md`, `IMPLEMENTATION_CONTRACT.md`, `spec.md`, and `tasks.md` before writing code"
- "Read all Depends-On tasks"
- "See `spec.md §X` for the pipeline"

Preferred replacements:

- "Applicable contract rules for this task: [3-6 bullets]"
- "`T21` done — added `SourceDocument` in `app/retrieval/types.py`; `GoogleDocsSourceConnector` in `gdocs_client.py`"
- "Pipeline: source connector -> normalized document -> chunking -> embeddings -> index"

Guardrails:

- if the implementation agent would need to open more than one extra document before starting, the prompt is probably under-digested
- if a task is routine and the prompt mostly contains references to canonical docs, the prompt is probably over-indexed
- compact prompts reduce token spend, but never omit a rule that materially changes correctness, safety, or interface compatibility

### Operational Load Distribution

To avoid burning one model family's limits unnecessarily, distribute work by role:

- **Claude / architecture-grade model**: Strategist, Phase 1 Validator, phase-boundary strategy review, deep review, architectural ambiguity resolution
- **Codex / implementation-grade model**: task execution, narrow-scope fixes, tests, lint, local refactors within declared file scope

Operational rules:
- do not spend architecture-grade context on routine file edits
- do not spend implementation-grade runs on broad architecture reasoning
- prefer small tasks with explicit file scope; this reduces token load for both sides
- prefer pre-digested implementation prompts; do not make Codex reconstruct narrow task context from multiple long docs unless the task genuinely needs broad retrieval
- run deep review only at phase boundaries or real risk boundaries, not after every small task
- compact `CODEX_PROMPT.md` and phase history regularly so both agents read summaries, not full history

---

## 1b. System Architecture — Layer Map

The workflow has seven layers. Each layer has a defined purpose, defined outputs, and a hard boundary with adjacent layers. Layers never cross into each other's responsibility.

```
┌─────────────────────────────────────────────────────────────────┐
│  LAYER 1: PLANNING                                               │
│  Strategist agent reads project description → produces all       │
│  Phase 1 artifacts before any code is written.                   │
│  Outputs: ARCHITECTURE.md, spec.md, tasks.md, CODEX_PROMPT.md,  │
│           IMPLEMENTATION_CONTRACT.md, CI workflow                │
└──────────────────────────────┬──────────────────────────────────┘
                               │
┌──────────────────────────────▼──────────────────────────────────┐
│  LAYER 2: ORCHESTRATION                                          │
│  Orchestrator reads state from files → decides action →          │
│  spawns agents → updates state → loops.                          │
│  Stateless across sessions. All state lives in files.            │
│  Output: Loop control, subagent invocations, state transitions   │
└──────────────────────────────┬──────────────────────────────────┘
                               │
┌──────────────────────────────▼──────────────────────────────────┐
│  LAYER 3: IMPLEMENTATION (Codex)                                 │
│  One task at a time. Reads exact file list. Writes code + tests. │
│  Never self-reviews. Never touches adjacent tasks.               │
│  Output: Code changes + tests + CODEX_PROMPT.md patch + commit   │
└──────────────────────────────┬──────────────────────────────────┘
                               │
┌──────────────────────────────▼──────────────────────────────────┐
│  LAYER 4: REVIEW (Two-Tier)                                      │
│  Tier 1 — Light: 1 agent, 6 security/contract checks per task    │
│  Tier 2 — Deep:  META → ARCH → CODE → CONSOLIDATED per phase     │
│  Output: Findings (P0/P1/P2/P3), REVIEW_REPORT.md, Fix Queue    │
└──────────────────────────────┬──────────────────────────────────┘
                               │
┌──────────────────────────────▼──────────────────────────────────┐
│  LAYER 5: QUALITY LOOP                                           │
│  Baseline tracking (tests must not decrease).                    │
│  P2 Age Cap (3-cycle limit → escalate, close, or defer to v2).  │
│  Append-only audit trail in docs/audit/.                         │
│  Output: Quality trend signal, finding lifecycle enforcement     │
└──────────────────────────────┬──────────────────────────────────┘
                               │
┌──────────────────────────────▼──────────────────────────────────┐
│  LAYER 6: AUDIT / TRACEABILITY                                   │
│  CODEX_PROMPT.md: immutable session state across interruptions.  │
│  IMPLEMENTATION_CONTRACT.md: immutable rules (ADR required).     │
│  ADRs: append-only architectural decisions.                      │
│  docs/audit/CYCLE{N}_REVIEW.md: append-only findings trail.     │
│  Typed commits: one logical change, one commit, traceable.       │
│  Output: Full reconstruct of any session from files alone        │
└──────────────────────────────┬──────────────────────────────────┘
                               │
┌──────────────────────────────▼──────────────────────────────────┐
│  LAYER 7: RUNTIME / CI                                           │
│  Runtime tier is selected proportionally: T0 managed/determin-   │
│  istic, T1 container/bounded worker, T2 ephemeral isolated       │
│  mutable runtime, T3 persistent privileged worker. CI verifies   │
│  the chosen runtime contract, service dependencies, integrity     │
│  references, and risky write verification evidence.              │
│  Output: Green/red signal per commit, baseline verification      │
└─────────────────────────────────────────────────────────────────┘
```

### Layer Boundaries — Hard Rules

| Rule | Why |
|------|-----|
| Implementation never reviews its own output | The Codex agent that writes the code never runs the review agents |
| Review never writes code | Review agents produce findings; Codex fixes them |
| Orchestrator never writes application code | It reads, decides, and spawns — no direct file edits in app/ |
| Planning precedes implementation | Phase 1 (Layer 1) must be complete before Layer 3 begins |
| CI gate is a layer boundary | No PR crosses from Layer 3 to Layer 4 if CI is red |
| Claims require evidence | Claimed files, tests, decisions, and eval updates must be verified against repo state |

---

## 2. Project Initialization (Phase 1)

Every project begins with a Phase 1 decision, but Phase 1 is mode-scoped. The
first decision is the adoption mode: Lean, Standard, or Strict. Do not force a
Lean project to produce Strict artifacts, and do not weaken Strict evidence
requirements for a high-risk project.

See `docs/adoption_modes.md` for the artifact matrix.

### Required Deliverables at End of Phase 1

| Artifact | Lean | Standard | Strict |
|----------|------|----------|--------|
| Problem fit note | Required | Required | Required |
| `docs/tasks.md` | Required | Required | Required |
| `docs/CODEX_PROMPT.md` or `AGENTS.md` | Required | Required | Required |
| `docs/IMPLEMENTATION_CONTRACT.md` | Contract-lite | Required | Required |
| CI or documented local verification command | Required | Required CI | Required CI with relevant gates |
| `docs/ARCHITECTURE.md` and `docs/spec.md` | Optional unless architecture/scope is non-trivial | Required | Required |
| `docs/DECISION_LOG.md` and `docs/IMPLEMENTATION_JOURNAL.md` | Optional | Required | Required |
| `docs/COGNITION_MANIFEST.md` | Optional | Optional | Required when cognition/vault/context packets are used |
| `docs/EVIDENCE_INDEX.md` | Optional | Optional unless recurring evidence exists | Required |
| Capability eval artifacts | Only for active capability behavior | Only for active capability behavior | Required for active capability behavior |

Lean projects still need explicit tasks, verification evidence, and review at
meaningful boundaries. They do not need fake cognition, proof, or eval artifacts.

### Continuity Artifacts

Use the continuity artifacts as follows:

- `docs/DECISION_LOG.md` is a retrieval index for major architectural, policy, and scope decisions. It is not a replacement for ADRs or `ARCHITECTURE.md`.
- `docs/IMPLEMENTATION_JOURNAL.md` records durable handoff context: why a change happened, what evidence was collected, and what the next agent must know.
- `docs/EVIDENCE_INDEX.md` is an optional proof index. It helps reviewers and implementers find prior tests, evals, and review reports without treating summaries as evidence.
- `docs/COGNITION_MANIFEST.md` is a repo-local map for agent-readable operational memory. It identifies canonical surfaces, retrieval scopes, known gaps, and generated-artifact policy. It is not an authority layer.
- `Context-Refs` in `docs/tasks.md` point an agent to the small set of prior docs that must be read before implementation.

### Why CI Is Set Up in Phase 1

CI is not a Phase 3 polish task. Setting it up in Phase 1 means:
- Every subsequent commit is automatically verified
- Baseline drift is caught immediately, not accumulated
- Review cycles can reference CI status as ground truth
- There is never a moment when "tests pass locally but CI is unknown"

Deferring CI past Phase 1 is a forbidden action. See Section 9.

### Establishing the Baseline

After the first passing tests, record the baseline in `docs/CODEX_PROMPT.md`:

```
Current Baseline: N passing tests
Last CI run: green
```

Every subsequent session starts by running `pytest` and comparing against this baseline. A session that produces fewer passing tests than the baseline has broken something and must not commit.

---

## 2a. Problem-First Entry Gate and Adoption Reality

Before selecting an agent shape, runtime tier, or capability profile, Phase 1 must
prove that the project is attached to a real operational pain. The playbook is a
governance and proof system, not a way to make an unvalidated AI idea look
production-ready.

### 2a.1 Problem-First Entry Gate

Every Phase 1 architecture package must answer:

- What concrete operational pain exists today?
- How is the team handling it now?
- Why are checklists, CI, ordinary review, scripts, or manual SOPs insufficient?
- Who is the first user, operator, or buyer who feels the pain?
- What would make v1 not worth adopting?
- What first metric or observation proves the system is useful in real work?

If these answers are missing or weak, do not proceed to an agentic build. Reduce
the next step to discovery, measurement, or a small deterministic improvement.

### 2a.2 Adoption Reality Gate

AI adoption claims must be scoped before implementation begins:

- name the work AI is expected to improve
- name the work AI will not replace
- keep human approval and accountability explicit
- list claims that cannot be made before evaluation evidence exists
- define what evidence is required to move from a good demo to a trusted workflow

Forbidden weak claims include broad promises such as "replace engineers",
"fully autonomous team", "production-ready swarm", or "AI-native transformation"
unless the architecture package also defines the exact workflow scope,
human-approval boundary, and metric that would make the claim testable.

This gate does not weaken ambition. It prevents demo energy from replacing
evidence. Agentic behavior is justified by measured need, not by executive
excitement or vendor narrative.

---

## 2b. Right-Sizing: Solution Shape, Governance, Runtime

Before enabling any complexity-bearing pattern, Phase 1 must answer three independent questions:

1. What solution shape is minimally sufficient?
2. What governance level is justified?
3. What runtime tier is justified?

These decisions are separate from the capability profiles. A project can be Agentic:OFF and still require Strict governance. A project can be Agentic:ON and still remain at Runtime T1 if the runtime stays bounded and non-privileged. Do not collapse these axes into one.

### 2b.1 Solution Shape Selection

Every project declares a primary solution shape in `docs/ARCHITECTURE.md`, with hybrid decomposition only where needed.

| Shape | Choose it when | Default posture |
|------|-----------------|-----------------|
| **Deterministic subsystem** | The problem is already formalizable: routing, validation, permissions, calculations, thresholds, transformations, retries, audit triggers | Prefer code + tests over LLM judgment |
| **Workflow orchestration** | The steps are known, ordered, and reviewable | Explicit step graph; human approval at defined boundaries |
| **Bounded ReAct / tool-using agent** | The system must choose among tools or iterate briefly under explicit limits | Termination contract, budget limits, authority boundaries |
| **Higher-autonomy agent** | The task requires longer-horizon planning, delegation, or mutable execution not well expressed as a fixed workflow | Stronger isolation, stronger governance, stronger rollback |
| **Hybrid decomposition** | Different subsystems need different levels of freedom | Deterministic by default; higher freedom only where justified |

The bias is downward: deterministic beats workflow when the behavior is formalizable; workflow beats agency when the steps are known; bounded agency beats freer autonomy when the task can be constrained.

### 2b.2 Anti-Overengineering Gate

Before turning ON complexity, the Strategist must answer all of the following:

- Why is a deterministic subsystem insufficient here?
- Why is a fixed workflow insufficient here?
- Why is a simple human-in-the-loop assistant insufficient here?
- Why is simple tool use without planning or loops insufficient here?
- Why is this capability needed now rather than deferred?

Weak answers mean the lower-complexity option should remain in place. "Future flexibility", "modern architecture", or "agents are powerful" are not valid justifications.

### 2b.3 Proportional Governance

Governance intensity scales with risk and criticality:

| Level | Typical fit | Required posture |
|------|--------------|------------------|
| **Lean** | Prototype, internal assistant, low-blast-radius workflow | Core artifacts, explicit tasks, light review, human approval at meaningful boundaries |
| **Standard** | Internal operational system, customer-facing but recoverable service | Full workflow, phase gates, stronger evaluation and audit trail |
| **Strict** | Business-critical, high-blast-radius, compliance-heavy, or privileged autonomous system | Strong approval boundaries, stronger evidence, stronger runtime and recovery controls |

Governance level changes how much control surface is justified. It does not
weaken the workflow's hard invariants: no self-review, explicit task state, test
or verification evidence, bounded correction, and human approval at meaningful
risk boundaries. Phase gates are required at the cadence justified by the mode;
Lean gates may be lightweight.

### 2b.4 Execution Substrate Selection

Runtime substrate is a proportional control, not the definition of the system.

| Tier | Meaning | Use when |
|------|---------|----------|
| **T0** | Deterministic or managed-service execution; no special isolated mutable runtime | Most app logic, validators, fixed workflows, managed integrations |
| **T1** | Container, devcontainer, or bounded worker runtime | Standard services, bounded tool execution, normal CI/workers |
| **T2** | Ephemeral microVM-class or similarly isolated mutable runtime | Risky autonomous tasks require shell/workspace/toolchain mutation with strong isolation and easy rollback |
| **T3** | Persistent VM-class or privileged long-lived isolated worker | Long-running autonomous execution with persistence, broader privilege, or continuity requirements. See `reference/solution_references.md` and `docs/dynamic_workflow_reference_policy.md` before adopting external runtime references. |

Select runtime tier by:
- autonomy level
- mutable runtime need
- shell/package/toolchain modification need
- privilege surface
- blast radius
- recovery / rollback need
- persistence need

Higher autonomy often increases runtime needs, but the relation is not automatic. An agent is not equal to a VM.

### 2b.5 Minimum Viable Control Surface

Every project should define the smallest control set that still matches its risk and autonomy. This is the **minimum viable control surface**.

Examples:
- Lean + T0 may need only explicit approval boundaries, tests, and audit triggers.
- Standard + T1 may also need tool schemas, unsafe-action gates, and evaluation artifacts.
- Strict + T2/T3 may additionally need egress rules, mutation boundaries, snapshots, rollback paths, and tighter approval gates.

Too little control creates unmanaged risk. Too much control creates dead process. The goal is proportional sufficiency.

### 2b.6 Agent System vs Runtime Substrate

Keep these concerns separate:

- **Agent system**: identity, goals, memory, tools, planning loop, budget, policy, audit, human approvals
- **Runtime substrate**: where execution happens and how isolated, mutable, or privileged it is

A deterministic system can run in a VM. An agent can run in a container. VM or microVM isolation may be justified for some autonomous code agents, but that is a runtime choice driven by risk, mutability, and recovery needs, not the definition of the agent itself.

---

## 2b.7 Model Selection and Inference Budgeting

If a system uses LLM inference, model choice must be treated as a measurable architecture decision, not a default.

Rules:
- choose models per workload or subproblem, not one model for the whole system by default
- ask "can this be deterministic?" before assigning any model at all
- if an LLM is required, choose the minimum sufficient model class for the job
- justify stronger models by measurable need: quality, latency, context window, or required capabilities
- track both estimated and measured inference cost; do not reason about quality in isolation from cost and latency

Evaluate model choice across these axes:
- task quality / success rate
- latency
- cost per call / per successful task
- context window
- required capabilities: function calling, multimodal input, reasoning depth, structured output

Price aggregators such as `llmpricing.dev` are useful comparison inputs, but not the sole source of truth. Final project decisions should be recorded in project artifacts together with measurement date and, where possible, vendor-source confirmation.

The Strategist should define:
- which workloads need no model
- which workloads can use a smaller / cheaper model
- which workloads justify escalation to a stronger model
- what metrics will prove the choice is still correct after implementation

### 2b.8 Cost Budget Guardrails

If a project uses LLM calls, agent loops, dynamic workflows, retrieval,
evaluators, or multi-agent review, cost must be declared before execution.

Rules:
- Lean projects may keep the budget inline in `docs/CODEX_PROMPT.md`,
  `AGENTS.md`, `docs/CONTRACT_LITE.md`, or task `Cost-Budget:` fields
- Standard/Strict projects use `docs/COST_BUDGET.md` when AI usage is
  recurring, multi-agent, dynamic-workflow based, multi-user, or materially
  costly
- recurring/material AI usage, prompt caching, batch lanes, dynamic routing,
  cascades, or non-trivial model tiering also require cost architecture in
  `docs/ai_cost_architecture.md` or an explicit Lean inline equivalent
- prompt caching requires a stable-prefix / volatile-suffix layout; volatile
  run state such as timestamps, current diffs, latest test output, and
  temporary diagnostics stays below the cache boundary
- dynamic routing and cascades require `docs/router_eval.md` before recurring
  or production use
- budget gates must cover model calls, retries, tool calls, fan-out, model
  escalation, and approval before overrun
- cost attribution should include project, task/workflow, role/agent, model,
  operator/user, feature/workload, and environment
- cost reduction is valid only when quality/eval and latency remain within the
  declared threshold
- measure cost per successful task, not only cost per call; failed cheap
  attempts, verifier calls, retries, tools, and estimated human rework count
  toward total cost
- a cheap model must not self-certify high-risk outputs in a cascade unless its
  confidence has been calibrated on the project eval set or an independent
  verifier gates escalation
- recurring or threshold-gated AI usage should emit provider-agnostic telemetry
  to `docs/ai_cost_telemetry.jsonl` or an equivalent source and run
  `tools/cost_rollup.py` in review/CI
- downstream projects can start from
  `templates/cost_adapters/python/telemetry_adapter.py`; this is an explicit
  provider boundary, not hidden SDK monkey-patching

See `docs/cost_budget_guardrails.md`, `docs/cost_telemetry_protocol.md`,
`docs/ai_cost_architecture.md`, `docs/cache_context_layout.md`,
`docs/provider_routing_policy.md`, `templates/COST_BUDGET.md`,
`templates/COST_ARCHITECTURE.md`, `templates/ROUTER_EVAL.md`, and
`tools/cost_rollup.py`.

### 2b.9 External Skill Security

External agent skills are supply-chain artifacts. They can package
instructions, code, scripts, references, assets, tool schemas, and metadata
that influence an agent with the agent's permissions. They are not installed or
enabled by default.

Rules:
- third-party, marketplace, vendor, GitHub, zip, or cross-project skills require
  trust evidence before install, update, enablement, or global exposure
- Standard/Strict projects use
  `docs/security/skills/{skill-name}/TRUST_RECORD.md` from
  `templates/EXTERNAL_SKILL_TRUST_RECORD.md`
- Lean projects may keep inline evidence only for instruction-only,
  project-local, low-risk skills with no scripts, tools, network, file writes,
  environment access, or MCP access
- executable, networked, MCP/tool-enabled, file/env-accessing, persistent, or
  global skills require source pin/signature/hash, declared capabilities,
  SkillSpector or equivalent scan evidence, finding triage, install scope, and
  human approval where needed
- CRITICAL/HIGH scan findings, hidden instructions, tool poisoning, credential
  harvesting, remote script execution, description-behavior mismatch, or
  unpinned executable dependencies block install unless formally accepted by a
  human owner
- a clean scanner report is evidence, not proof of safety; a signature proves
  reviewed-artifact integrity, not safety

Use `docs/external_skill_security_policy.md`,
`templates/EXTERNAL_SKILL_TRUST_RECORD.md`, and
`templates/skills/external_skill_security_skill.md`. Use
`tools/skill_security_gate.py` in CI or review when skills are present.

---

## 2c. Capability Profiles

A Capability Profile is an optional architectural mode that can be activated during Phase 1. Each profile extends the base workflow with profile-specific artifacts, rules, review checks, state tracking, and evaluation criteria. Profiles are declared in the `## Capability Profiles` table in `docs/ARCHITECTURE.md`.

Profiles are not the first escalation step. First choose the solution shape, governance level, and runtime tier. Then turn a profile ON only if it governs real behavior in that chosen shape.

**RAG is the most fully elaborated reference implementation, but Tool-Use, Agentic, Planning, and Compliance are also supported profiles.**

---

### Profile: RAG

RAG (Retrieval-Augmented Generation) is **not a default requirement**. It is an optional architectural mode that the Strategist must explicitly enable or disable during Phase 1. Its evaluation artifact is `docs/retrieval_eval.md`.

#### RAG Status: ON | OFF

The Strategist declares the RAG status in the `## Capability Profiles` table in `docs/ARCHITECTURE.md`:

```
| RAG | ON  | docs/retrieval_eval.md | project uses retrieval-backed architecture |
| RAG | OFF | docs/retrieval_eval.md | project does not use retrieval; standard prompting only |
```

This decision is made once, in Phase 1, and treated as an architectural constraint for all subsequent phases. Changing it requires an ADR.

#### When to Turn RAG ON

Turn RAG Profile ON when one or more of the following is true:

| Signal | Example |
|--------|---------|
| Large document/corpus context that does not fit in a prompt | Policy manuals, legal documents, multi-volume runbooks |
| Knowledge that changes faster than the code deploy cycle | Frequently updated FAQs, live regulations, evolving product catalogs |
| Citations or evidence are required in the output | Answers must reference source documents with traceability |
| Document-heavy sources | PDFs, markdown corpora, internal wikis, technical manuals |
| Retrieval needed not just for end-user chat but also for agent or tool context | An agent that must look up current pricing or policy before acting |

When none of these signals are present, RAG Profile is OFF. Do not add retrieval infrastructure speculatively.

#### Additional Artifacts When RAG Status = ON

If the Strategist declares RAG Status ON, the following additional artifacts must be produced in Phase 1:

| Artifact | Path | Purpose |
|----------|------|---------|
| RAG Architecture section | `docs/ARCHITECTURE.md §Profile: RAG > §RAG Architecture` | Ingestion pipeline, query-time pipeline, corpus description, index strategy, retrieval / embedding strategy |
| Retrieval spec section | `docs/spec.md §Retrieval` | What sources are indexed, update frequency, expected query types, citation requirements |
| RAG tasks | `docs/tasks.md` | Separate tasks for ingestion pipeline and query-time retrieval (never merged into a single task) |
| Retrieval acceptance criteria | `docs/tasks.md` (per task) | Retrieval-specific criteria: recall targets, latency bounds, insufficient-evidence path |
| Profile contract rules | `docs/IMPLEMENTATION_CONTRACT.md §Profile Rules: RAG` | Corpus isolation, schema versioning, stale-index handling policy |
| Profile state block | `docs/CODEX_PROMPT.md §Profile State: RAG` | Retrieval baseline, open retrieval findings, index schema version, pending reindex |
| Evaluation artifact | `docs/retrieval_eval.md` | Retrieval quality metrics with own lifecycle (separate from code quality) |

#### Retrieval / Embedding Strategy

When RAG Status = ON, embedding strategy is an architectural decision, not an implementation footnote.

The Strategist must declare one of:

- **No retrieval** — RAG stays OFF; no embedding system is introduced
- **Text-only retrieval** — default baseline when retrieval is needed
- **Multimodal retrieval** — optional advanced path; justify explicitly

Text-only retrieval remains a valid and often optimal baseline. Multimodal retrieval is justified only when the product truly depends on retrieving non-text evidence as first-class input rather than by converting everything to text or metadata.

If multimodal retrieval is selected, `docs/ARCHITECTURE.md` must state:

- modalities in scope now (for example: text + images, or text + PDFs)
- why text-only retrieval is insufficient
- expected value vs. added complexity, latency, and cost
- model stability status (stable vs. preview / experimental)
- fallback or migration path if the chosen model changes, degrades, or is withdrawn
- evaluation plan, including comparison against a text-only baseline where feasible

Do not enable multimodal retrieval for "future flexibility" alone. Unused modalities are architecture drift.

#### RAG Workflow Shape

When RAG Status = ON, the retrieval system has two distinct pipelines. These are separate responsibilities and must never be merged into a single task or service.

**Ingestion pipeline** (offline, scheduled, or event-driven):
```
extract → normalize → chunk → embed → index
```

**Query-time pipeline** (online, per-request):
```
query analyze → retrieve → rerank/filter → assemble evidence → answer | insufficient_evidence
```

The `insufficient_evidence` path is not optional. If the retrieved evidence does not support an answer, the system must return `insufficient_evidence` rather than hallucinating a response. This path must have an explicit acceptance criterion and a test.

The retrieval architecture must also declare whether retrieval is text-only or multimodal. If multimodal, list the supported modalities explicitly and explain why a text-only baseline is insufficient.

#### Retrieval Quality is Evaluated Separately from Code Quality

Retrieval correctness cannot be verified by code review alone. When RAG Status = ON, the review cycle must include retrieval-specific checks:

- **Recall audit**: Does the system retrieve the right documents for representative queries?
- **Evidence assembly**: Is the assembled context coherent and relevant to the query?
- **Insufficient-evidence path**: Is the fallback path exercised in tests with queries that should not be answerable?
- **Index staleness**: Is there a defined maximum age for indexed documents? Is it enforced?
- **Corpus isolation**: If multi-tenant, are corpus boundaries enforced at the retrieval layer?
- **Modality fit**: If multimodal retrieval is enabled, does each enabled modality improve the target workflow enough to justify its cost and latency?
- **Baseline comparison**: If multimodal retrieval is enabled, is it compared against a text-only baseline rather than assumed superior?

These checks are added to `PROMPT_2_CODE.md` (code review) and `PROMPT_1_ARCH.md` (architecture review) when RAG Status = ON.

#### RAG-Specific Risks

The following risks apply only to RAG-profile projects and must be documented in `docs/ARCHITECTURE.md §Profile: RAG > §Risks` when RAG Status = ON:

| Risk | Description | Mitigation |
|------|-------------|------------|
| Hallucination on weak evidence | Model answers confidently despite low-quality retrieval | Require confidence threshold; implement `insufficient_evidence` path |
| Schema drift | Embedding model or chunk format changes invalidate the index | Version the index schema; re-index on model change; enforce via ADR |
| Stale index | Indexed documents fall out of date silently | Define max index age; add staleness check to health endpoint |
| Corpus isolation failure | Retrieval crosses tenant or classification boundaries | Enforce corpus-level ACLs at the retrieval layer, not just application layer |
| Retrieval latency regression | Adding reranking or larger corpora degrades p95 latency | Set latency acceptance criteria per retrieval task; track in baseline |
| Multimodal overreach | Extra modalities add cost and complexity without measurable value | Default to text-only; require explicit justification and text-baseline comparison before enabling multimodal |
| Preview model instability | Preview / experimental embedding model changes, degrades, or is withdrawn | Record stability status, fallback target, and migration / re-index plan in architecture |

#### Orchestrator Handling of RAG Work

When RAG Status = ON, the Orchestrator applies a **stricter review path** to retrieval-related tasks:

- All tasks tagged `rag:ingestion` or `rag:query` trigger a **deep review**, not just a light review, regardless of phase boundary.
- The ARCH review must explicitly verify corpus isolation and pipeline separation.
- The CODE review must verify the `insufficient_evidence` path is tested.
- P2 findings on retrieval components escalate to P1 at the next cycle (the Age Cap is reduced from 3 cycles to 1 cycle for retrieval-critical findings).

Tag retrieval tasks in `tasks.md` with a `Type:` field:

```markdown
Type: rag:ingestion   # ingestion pipeline tasks
Type: rag:query       # query-time retrieval tasks
```

The Orchestrator reads this tag to apply the stricter review path.

---

## 2d. Capability Profiles

Beyond RAG, a system may require Tool-Use, Agentic, or Planning capabilities. Each is an optional architectural mode that the Strategist must explicitly declare in Phase 1. Like RAG, all four profiles are OFF by default. Do not enable them speculatively.

### Profile Definitions

| Profile | Definition | NOT |
|---------|-----------|-----|
| **RAG** | The application retrieves from a managed corpus at query time to ground its outputs. Requires: ingestion pipeline, query-time retrieval, corpus isolation, `insufficient_evidence` path | Not a simple tool call to an external search API without a managed corpus and ingestion pipeline |
| **Tool-Use** | The LLM calls external functions or APIs (tools) at inference time — stateless, per-request invocations. Governs: side effects, idempotency, permissions, retries, unsafe-action controls, tool schema | Not Agentic (no decision loop); not RAG (no corpus, no ingestion) |
| **Agentic** | The LLM operates in a decision loop: observe → decide → act → observe, until a termination condition. Governs: roles, delegation, coordination, handoffs, authority boundaries, loop termination contract | Not Tool-Use (stateless single-call); not Planning (Agentic produces actions, not plans as primary deliverables) |
| **Planning** | The LLM produces structured plans — task graphs, step-by-step procedures, decision trees — as the **primary deliverable** consumed by humans or downstream systems. Requires: plan schema, plan validation, plan-to-execution contract | Not the ORCHESTRATOR (which controls the development loop, not application behavior); not agentic chain-of-thought (internal planning is not this profile) |

**Planning invariant:** Planning Profile concerns application runtime behavior. ORCHESTRATOR concerns the development workflow. These are invariantly distinct levels — never merge them.

### Compatibility Matrix

```
             RAG        Tool-Use    Agentic     Planning
RAG          —          ✅ §        ✅          ✅
Tool-Use     ✅ §        —          ✅ +        ✅
Agentic      ✅          ✅ +        —           ✅
Planning     ✅          ✅          ✅           —
```

**`✅`** — compatible; both profiles declared independently.
**`✅ §`** — compatible; semantic ownership rule applies (see below).
**`✅ +`** — compatible; audit checklists are additive (see below).

### Semantic Ownership Rule (RAG + Tool-Use)

> **Semantic ownership beats implementation mechanism.**

If a task changes retrieval semantics — corpus structure, chunking logic, embedding model, query policy, `insufficient_evidence` behavior, or index schema — it is **RAG-owned**, regardless of whether the implementation routes through a tool call, HTTP API, or direct SDK call.

The task `Type:` tag is the source of truth. The implementation type is not.

```
# Example: adapter swap that touches retrieval semantics
Task: "Replace vector index adapter"
Code touches: API client (looks like tool code)
Tag: Type: rag:ingestion
Ownership: RAG — semantic wins; RET-N checks apply, not TOOL-N
```

### Capability Signal Patterns

The Orchestrator uses file path patterns to infer which profile a task touches. This is used for two checks:

1. **Pre-implementation (Step 0-E):** if the task's file scope contains a HIGH-confidence pattern but lacks the corresponding `Type:` tag → `TAG_WARNING` + stop until user confirms.
2. **Post-implementation (Step 3):** if Codex's "Files modified" list matches a profile different from the current tag → `SEMANTIC_MISMATCH` (non-blocking, surfaces to light reviewer).

| File path pattern (substring match) | Profile | Confidence |
|--------------------------------------|---------|------------|
| `retrieval/`, `embedding`, `chunk`, `index`, `corpus`, `ingestion`, `rerank` | RAG | HIGH |
| `tools/`, `tool_schema`, `function_call`, `@tool`, `tool_catalog` | Tool-Use | HIGH |
| `plan_schema`, `plan_graph`, `plan_valid` | Planning | HIGH |
| `agent/`, `loop`, `handoff`, `termination` (app code only, not workflow docs) | Agentic | MEDIUM |

HIGH-confidence match + missing tag → **STOP** (Step 0) or **SEMANTIC_MISMATCH** (Step 3).
MEDIUM-confidence match → warning only, no stop.

This is a heuristic, not a guarantee. Semantic ownership (see above) still takes precedence: a file touching `tools/` may correctly carry `rag:ingestion` if it changes retrieval semantics.

### Capability Check Scenarios

Worked examples that show expected Orchestrator behavior end-to-end. Use these to calibrate the signal patterns and verify the workflow does not overfire.

**Workflow effect vocabulary** (used in scenarios below):

| Effect | Meaning |
|--------|---------|
| `BLOCK` | Orchestrator stops before spawning the implementer; user must confirm or correct tag |
| `TASK_NOT_COMPLETE` | Implementation ran but Orchestrator withholds `✅`; light review found a check failure |
| `LIGHT_REVIEW_EXPANDED` | Light review runs SEC-1…6 + CF + profile-conditional checks (RAG-L1/3, TOOL-L1, AGENT-L1, PLAN-L1) |
| `DEEP_REVIEW_EXPANDED` | Phase boundary deep review runs the profile-specific check set (RET-N, TOOL-N, AGENT-N, PLAN-N) in addition to SEC+QUAL+CF |

---

**Scenario 1 — TAG_WARNING: missing rag tag on retrieval file**
```
Task:            T05 — Update embedding model
Files scope:     app/retrieval/embedding.py
Type:            (none)
Active profiles: RAG:ON

Step 0-E:  HIGH match — "embedding" in path, no rag:* tag → TAG_WARNING + STOP
Step 3:    not reached
Light:     not reached
Workflow effect: BLOCK
```

**Scenario 2 — Negative control: no capability impact**
```
Task:            T06 — Fix error message copy in user-facing UI
Files scope:     app/ui/messages.py, tests/test_ui.py
Type:            (none)
Active profiles: RAG:ON, Tool-Use:ON

Step 0-E:  no HIGH or MEDIUM pattern matches → OK
Step 3:    no pattern match in modified files → OK
Light:     SEC-1…6 + CF only (no profile-conditional checks, no capability tag)
Workflow effect: none (normal flow)
```
> This confirms the check does not overfire on files unrelated to any active profile.

**Scenario 3 — SEMANTIC_MISMATCH: wrong tag detected post-implementation**
```
Task:            T07 — Swap vector index adapter
Files scope:     app/tools/vector_client.py   (in tools/ but changes retrieval semantics)
Type:            tool:schema   (tagged incorrectly — semantic ownership not applied)
Active profiles: RAG:ON, Tool-Use:ON

Step 0-E:  "tools/" matches Tool-Use HIGH; tool:schema tag present → OK (no warning)
           Pre-impl check cannot detect semantic intent — only presence.
Step 3:    Codex also modified app/retrieval/index_schema.py →
           "retrieval/" + "index" match RAG HIGH; tag is tool:schema →
           SEMANTIC_MISMATCH (non-blocking): "signal suggests RAG, tag is Tool-Use; verify semantic ownership"
Light:     TOOL-L1 check runs (because tag is tool:schema) +
           reviewer sees SEMANTIC_MISMATCH in state block → manually verifies RET-N compliance
Workflow effect: TASK_NOT_COMPLETE if reviewer confirms RAG ownership and tag is wrong
                 Correct fix: change Type: to rag:ingestion, re-run from Step 3.5
```
> Shows why post-impl detection is necessary: pre-impl saw `tools/` and passed. Post-impl caught the retrieval file added by Codex.

**Scenario 4 — Mixed-profile: semantic ownership + additive checks**
```
Task:            T08 — Add research agent that calls retrieval tool
Files scope:     app/agents/research_agent.py, app/tools/retrieval_tool.py
Type:            rag:query + agent:loop   (dual tag — additive checks rule)
Active profiles: RAG:ON, Agentic:ON, Tool-Use:ON

Step 0-E:  "retrieval/" → RAG HIGH; rag:query present → OK
           "agent/" → Agentic MEDIUM → warn-only, no stop
           "tools/" → Tool-Use HIGH; but rag:query tag present and semantic ownership applies
             → no TAG_WARNING (RAG tag covers the tools/ file per semantic ownership rule)
Step 3:    modified files match rag:query + agent:loop tags → OK
Light:     RAG-L1, RAG-L2 (rag:query tag) + AGENT-L1 (agent:loop tag) — 3 extra checks
           TOOL-L1 NOT run — tool:unsafe tag not present
Workflow effect: LIGHT_REVIEW_EXPANDED (RAG-L + AGENT-L)
                 DEEP_REVIEW_EXPANDED: RET-N (RAG) + AGENT-N (Agentic); TOOL-N not triggered
```
> TOOL-N does not fire even though Tool-Use is ON, because the task tag is `rag:query`. TOOL-N fires only for `tool:schema` or `tool:unsafe` tagged tasks. Semantic ownership keeps RET-N as the governing check set for `app/tools/retrieval_tool.py`.

---

### Additive Checks Rule (Agentic + Tool-Use)

When Agentic and Tool-Use are both ON, their audit checklists are **additive** for tasks that touch both domains. Neither profile subsumes the other:

- **Tool-Use** owns: side effects, idempotency, permissions, retries, unsafe actions, tool schema definition
- **Agentic** owns: roles, delegation, coordination, handoffs, authority boundaries, loop termination

A task tagged `tool:call` + `agent:handoff` receives TOOL-N **and** AGENT-N checklists.

### Audit Check Ownership by Active Profiles

| Active profiles | Check set applied |
|-----------------|-------------------|
| RAG only | RET-N |
| Tool-Use only | TOOL-N |
| Agentic only | AGENT-N |
| Planning only | PLAN-N |
| RAG + Tool-Use | RET-N for `rag:*` tasks; TOOL-N for other tool tasks |
| RAG + Agentic | RET-N for `rag:*` tasks; AGENT-N for loop/agent tasks |
| Agentic + Tool-Use | AGENT-N + TOOL-N (additive) |
| All four active | Each profile governs its tagged tasks; semantic ownership rule applies for retrieval tasks |

### Orchestrator Dispatch — Tag-Based, Not Profile-Based

The Orchestrator dispatches on normalized task tags, not profile names. Each active profile registers deep review trigger tags. A deep review fires if **any** tag from any active profile matches the current task:

| Profile | Deep review trigger tags |
|---------|--------------------------|
| RAG | `rag:ingestion`, `rag:query` |
| Tool-Use | `tool:schema`, `tool:unsafe` |
| Agentic | `agent:loop`, `agent:handoff`, `agent:termination` |
| Planning | `plan:schema`, `plan:validation` |

Adding a new profile means registering new tags. The Orchestrator dispatch logic itself does not change.

### Declaring Profiles in ARCHITECTURE.md

```markdown
## Capability Profiles

| Profile   | Status | Declared in Phase | Notes |
|-----------|--------|-------------------|-------|
| RAG       | ON     | 1                 | Retrieval via managed vector corpus |
| Tool-Use  | OFF    | —                 | — |
| Agentic   | ON     | 1                 | Single-agent loop; terminates on task completion |
| Planning  | OFF    | —                 | — |
```

This declaration is made once in Phase 1 and treated as an architectural constraint. Changing any profile from OFF to ON (or vice versa) after Phase 1 requires an ADR.

### CODEX_PROMPT.md State Blocks

Each active profile gets its own state block. Blocks are independent. The task `Type:` tag determines which block is updated after each task completes.

```markdown
## RAG State        ← include only if RAG Profile = ON
## Tool-Use State   ← include only if Tool-Use Profile = ON
## Agentic State    ← include only if Agentic Profile = ON
## Planning State   ← include only if Planning Profile = ON
```

### For profile authors — The 9-Property Invariant

_Skip this section unless you are designing a new Capability Profile._

Every Capability Profile must define all nine of the following properties before it is activated. RAG demonstrates all nine — use it as the template.

| # | Property | What it covers |
|---|----------|----------------|
| 1 | **Decision Gate** | Explicit ON/OFF criteria in Phase 1 (Strategist decision) |
| 2 | **Architecture Sections** | Additional sections in `docs/ARCHITECTURE.md` when ON |
| 3a | **Spec Sections** | Additional sections in `docs/spec.md` when ON |
| 3b | **Task Type Namespace** | Profile-scoped task tags (e.g. `rag:ingestion`, `rag:query`) |
| 4 | **Implementation Contract Rules** | `## Profile Rules: {name}` section in `IMPLEMENTATION_CONTRACT.md` |
| 5 | **Orchestrator Behavior** | How the orchestrator detects and reacts to active profile and profile task tags |
| 6 | **Profile State Block** | `## Profile State: {name}` block in `CODEX_PROMPT.md` |
| 7 | **Audit Extensions** | Conditional check blocks in `PROMPT_1_ARCH.md` and `PROMPT_2_CODE.md` |
| 8 | **Evaluation Artifact** | A dedicated evaluation document with its own lifecycle (e.g. `docs/retrieval_eval.md`) |

A profile that omits any property is incomplete and must not be activated.

### Evaluation Invariant

Every active Capability Profile MUST define:
- **evaluation method** — what is measured and how (e.g. hit@k + MRR for RAG; schema validity + side-effect correctness for Tool-Use)
- **baseline** — reference values established in Phase 1, before any capability behavior is in production
- **regression criteria** — what constitutes a degradation that blocks task completion

Evaluation is **not optional**. Evaluation is required whenever capability behavior changes.

Evaluation trigger tags by profile (task `Type:` field):

| Profile | Evaluation trigger tags |
|---------|-------------------------|
| RAG | `rag:ingestion`, `rag:query` |
| Tool-Use | `tool:schema`, `tool:unsafe`, `tool:call` |
| Agentic | `agent:loop`, `agent:handoff`, `agent:termination` |
| Planning | `plan:schema`, `plan:validation` |

A task whose `Type:` tag matches any row above is **not complete** until:
1. The profile's evaluation artifact is updated with current results.
2. Current results are compared against the baseline.
3. Any regression is documented and either justified or escalated as P1.

"Tests are green" does not satisfy this requirement. Evaluation is a separate gate.

---

## 2e. Session Start Ritual — The Loop Mechanism

This is the mechanism that makes the workflow run autonomously without manual step-by-step prompting.

### The Problem It Solves

Without a structured session start, the developer acts as the orchestrator — manually triggering each step (implement, review, archive, doc update, phase report). Each pause is a gap where context is lost and steps get skipped.

With the ritual, the orchestrator drives the entire cycle from a single paste. The developer's only job is approving phase gates and resolving blockers.

### How It Works

Every session begins with a single action:

```
/orchestrate
```

This slash command reads `docs/prompts/ORCHESTRATOR.md` and executes it. It is installed automatically when a project is bootstrapped — the file lives at `.claude/commands/orchestrate.md`. If the command is not available (e.g. legacy project), fall back to pasting the full contents of `docs/prompts/ORCHESTRATOR.md` manually.

The orchestrator then:
1. Reads `docs/CODEX_PROMPT.md` and `docs/tasks.md` to determine current state
2. Prints an `=== ORCHESTRATOR STATE ===` block showing what it sees
3. Drives the full loop: Fix Queue → Strategy → Implement → Light Review → (if phase boundary) Deep Review → Archive → Doc Update → Phase Report → checkpoint → next task

No manual prompting is needed between steps. The orchestrator stops only when:
- A task is blocked `[!]` and needs human input
- A P0 finding cannot be resolved after 2 attempts
- All tasks are complete
- An API rate limit is hit (sends notification with resume time)
- A transient provider failure persists after one retry (prints `PROVIDER_FAILURE:` and saves checkpoint)

A budget-interrupted task (implementation agent returns BLOCKED citing context or iteration limits) is **not** a stop condition — the Orchestrator adds remaining work to the Fix Queue and continues normally.

### What ORCHESTRATOR.md Must Contain

Every project's `docs/prompts/ORCHESTRATOR.md` must have all 7 steps filled in with project-specific values:

| Placeholder | What to replace with |
|---|---|
| Project name | Used in all agent system prompts |
| Project root | Absolute path on disk |
| Implementation agent command | `codex exec` or `Agent tool (general-purpose)` — whichever is available |
| Test command | `pytest tests/ -q` or `python3 -m unittest discover tests/ -q` |
| Lint command | `ruff check` or skip if not enforced |
| Notification channel | Telegram bot, Slack, desktop notify, or remove if not needed |

The template is in `prompts/ORCHESTRATOR.md` in this playbook. Copy it, fill the placeholders, commit it as `docs/prompts/ORCHESTRATOR.md` in your project.

### Required Audit Prompt Files

The deep review pipeline (Steps 4.0–4.3) references four prompt files that must exist in `docs/audit/`:

| File | Purpose |
|---|---|
| `PROMPT_0_META.md` | Snapshot current state, define review scope |
| `PROMPT_1_ARCH.md` | Check architectural drift vs spec + contracts |
| `PROMPT_2_CODE.md` | Security and quality checklist per file |
| `PROMPT_3_CONSOLIDATED.md` | Produce REVIEW_REPORT.md + patches for tasks.md and CODEX_PROMPT.md |
| `AUDIT_INDEX.md` | Running log of all review cycles and archive entries |

Templates for all five are in the `prompts/audit/` directory of this playbook.

### Retrofit for Existing Projects

If a project already has code but lacks the workflow scaffolding:

1. Prefer
   `python3 /path/to/AI_workflow_playbook/tools/init_playbook_project.py <repo> --mode standard`
   to copy the starter kit without overwriting existing files.
2. Create or update `docs/CODEX_PROMPT.md` with current baseline and open
   findings.
3. Create `docs/IMPLEMENTATION_CONTRACT.md` with project-specific rules.
4. Add `.github/workflows/ci.yml`.
5. Copy and fill `docs/prompts/ORCHESTRATOR.md`.
6. Copy audit prompt templates to `docs/audit/`.
7. Create `docs/audit/AUDIT_INDEX.md` (start at Cycle 1).

After retrofit, paste ORCHESTRATOR.md and the loop runs identically to a greenfield project.

For project-fit screening and a practical retrofit sequence, see
`docs/project_fit_guide.md` and `docs/usage_guide.md`.

### Selective Heavy-Task Mode

Most work should stay on the normal loop. A heavier proof-first path is justified only when risk, irreversibility, or verification difficulty is materially higher than normal.

Typical triggers:

- security boundary changes
- migrations or destructive data changes
- retrieval semantics changes
- tool-side-effect safety logic
- high-blast-radius refactors

Recommended heavy-task add-ons live in task-local artifacts and are documented in `docs/heavy_task_mode.md`.
This is a selective extension, not a mandatory mode for every task.

---

## 3. Phase Structure

### What a Phase Is

A phase is a coherent unit of work that takes the project from one stable state to the next. A phase contains one or more tasks from `tasks.md`. Tasks within a phase may run sequentially or — if independent — in parallel via parallel subagents.

Phases are sequential. Phase N is never started until the Phase N-1 gate is passed.

### Phase Gate Criteria

All of the following must be true before a phase is closed:

- [ ] All tests pass (`pytest` exits 0)
- [ ] Ruff is clean (`ruff check` exits 0, `ruff format --check` exits 0)
- [ ] All P1 findings from the review cycle are resolved
- [ ] `docs/CODEX_PROMPT.md` is updated with new baseline, next task, and open findings
- [ ] Review cycle report saved to `docs/audit/CYCLE{N}_REVIEW.md`
- [ ] Human has reviewed and approved

### CODEX_PROMPT.md at Phase Boundaries

`CODEX_PROMPT.md` must be updated before the commit that closes a phase. It must contain:
- Current baseline (number of passing tests)
- Next task (the first task of the next phase, or "COMPLETE" if done)
- Open findings from the review cycle (P2s that survived, P3s of note)
- Fix Queue (any items deferred to next phase)

---

## 4. Task Execution — Codex Agent Protocol

Each task is executed by a Codex subagent. The orchestrator spawns the subagent with a precise prompt. The subagent operates in its own context window.

### Pre-Task Protocol (skip nothing)

The following steps are mandatory before writing any implementation code:

1. **Read the orchestrator's inline task digest first** — it should already contain the assignment, acceptance criteria, file scope, dependency facts, and the applicable rules for this task.
2. **Read the current task entry in `tasks.md` only as needed** — use it to confirm exact acceptance criteria, file scope, or notes, not as a default excuse to broad-read unrelated context.
3. **Read Depends-On tasks, `Context-Refs`, and canonical docs only when the digest is insufficient** — this is mandatory for architecture changes, risky boundaries, open findings, or interface-sensitive tasks.
4. **Run `pytest`** to capture the pre-task baseline. Record the number: `N passing, M failed`.
5. **Run `ruff check`** — must exit 0. Do not begin if ruff is not clean. Fix ruff issues first, commit them separately.
6. **Write tests before or alongside implementation.** No task is complete until every acceptance criterion has a passing test.

### During Implementation

- Work on one task at a time. Do not begin the next task until the current one is committed.
- Read only the files you need. Use `grep` to find relevant lines; read only those sections.
- Do not modify files outside the task's stated scope without explicit justification.
- If you discover a dependency or interface mismatch, stop and report it. Do not silently patch adjacent tasks.

### Post-Task Protocol

1. Run the full pre-commit check suite:
   - `ruff check app/ tests/`
   - `ruff format --check app/ tests/`
   - `pytest` — verify baseline increased or held (never decreased)
2. Update `docs/CODEX_PROMPT.md`:
   - New baseline
   - Next task
   - Any open findings discovered during this task
3. Commit with a granular commit message. One logical change per commit.
4. If the task produced multiple logical changes (e.g., a migration + a service + tests), use multiple commits.

### Codex Prompt Structure (from Orchestrator)

When the orchestrator spawns a Codex subagent, the prompt must specify:

```
Task: T{NN} — {task name}
Files to read: [exact list]
Files to modify: [exact list]
Files to create: [exact list]
Expected output: [what you return when done]
Acceptance criteria: [copied from tasks.md]
Pre-task baseline: {N} passing tests
```

Vague Codex prompts produce vague results. Precise prompts produce verifiable results.

---

## 5. Review Cycle Structure

The review cycle runs after each phase. It consists of four sequential review agents. Each is a subagent with its own context window.

### PROMPT_1: META Review

**Question answered:** Did the implementation follow the process?

Checks:
- Were all acceptance criteria from `tasks.md` implemented?
- Is each acceptance criterion covered by a test?
- Was the pre-task baseline captured and recorded?
- Was `docs/CODEX_PROMPT.md` updated at the phase boundary?
- Were any forbidden actions taken (see Section 9)?
- Was CI passing at the time of the phase gate commit?

Output: list of META findings (compliance gaps), each tagged P1/P2/P3.

### PROMPT_2: ARCH Review

**Question answered:** Does the implementation match the architecture?

Checks:
- Do new components appear in `docs/ARCHITECTURE.md`? If not, is an ADR warranted?
- Are new route handlers thin (delegate to services)?
- Are services testable without HTTP (accept primitives and sessions)?
- Is all SQL parameterized with named params?
- Is `SET LOCAL` used instead of session-level `SET` (for multi-tenant systems)?
- No PII in log messages, span attributes, or metrics?
- Shared tracing module used — no inline noop spans?
- Authorization enforced on every new route?

Output: list of ARCH findings, each tagged P1/P2/P3.

### PROMPT_3: CODE Review

**Question answered:** Does the code meet quality standards?

This review reads actual code. It:
- Verifies every finding from PROMPT_1 and PROMPT_2 against the actual source files
- Identifies additional code-level issues (error handling gaps, type errors, missing edge cases, security issues)
- Reviews test quality (are tests actually asserting behavior, or just running?)
- Checks for common anti-patterns

Severity tags:
- **P1** — must be fixed before the next phase gate. Blocks the phase.
- **P2** — must be fixed within 3 review cycles (see P2 Age Cap rule below). Does not block the current phase gate.
- **P3** — optional improvement. Log it, address it if convenient.

Output: consolidated findings with severity tags, file references, and specific line numbers where applicable.

### PROMPT_4: CONSOLIDATED Review

**Question answered:** What is the official state of this phase?

This agent:
- Merges findings from PROMPT_1, PROMPT_2, and PROMPT_3
- Deduplicates overlapping findings
- Produces the cycle report: `docs/audit/CYCLE{N}_REVIEW.md`
- Determines which P1s must be resolved before the gate passes
- Updates `docs/CODEX_PROMPT.md` with open findings

The cycle report is append-only. Do not edit previous cycle reports.

### P2 Age Cap Rule

Any P2 finding that remains open for more than 3 consecutive review cycles MUST be:
- Closed (resolved), OR
- Escalated to P1 (and resolved before the next phase gate), OR
- Formally deferred to v2 (documented in an ADR, removed from open findings)

A P2 finding cannot age indefinitely. The Age Cap rule prevents the finding backlog from becoming a graveyard.

### Running Reviews Concurrently

PROMPT_1 (META) and PROMPT_2 (ARCH) can run concurrently — they read different things. PROMPT_3 depends on their outputs. PROMPT_4 depends on PROMPT_3. So the sequence is:

```
[PROMPT_1 || PROMPT_2] → PROMPT_3 → PROMPT_4
```

### 5.5 Optional: Simplification Pass

A user-triggered pass focused on reducing redundancy, dead code, over-abstraction, and over-comment density. Runs separately from the mandatory META → ARCH → CODE → CONSOLIDATED cycle. It is opt-in and experimental — see §8 Experiment E5 in the integration assessment.

- **Trigger:** explicit user invocation (e.g. via `templates/.claude/commands/simplify.md`). Never automatic. Never part of the mandatory phase-boundary cycle.
- **Scope:** a user-named file or directory list, or — only as fallback — the scope from the most recent META analysis.
- **Output:** `docs/audit/SIMPLIFICATION_REPORT.md` (overwrite per pass; row prefix `SIMP-N` so it does not collide with `CYCLE-N`).
- **Approved simplifications** become normal Codex tasks with behavior-preservation acceptance criteria — existing tests pass, a new test pins the prior behavior when needed, and the complexity metric improves by a stated delta. The task runs through normal light or deep review like any other.
- **Findings that would change behavior** are rejected by the Simplification Reviewer. They do not enter `tasks.md`.
- The simplification pass does not replace, gate, or alter the mandatory phase-boundary review cycle. It does not close existing review findings, drop tests, or relax any rule in `IMPLEMENTATION_CONTRACT.md` or any active capability profile.

See `prompts/audit/PROMPT_SIMPLIFY.md`, `templates/skills/simplification_skill.md`, and the `Simplification Pass` row in `reference/optional_skills.md`.

---

## 6. Immutable Implementation Rules

These rules apply to every project that uses this playbook. They must appear verbatim in `docs/IMPLEMENTATION_CONTRACT.md`. They are never changed without an explicit Architectural Decision Record (ADR) filed in `docs/adr/`.

### Universal Rules

**SQL safety**
- All SQL is parameterized. Use `text()` with named params: `text("SELECT ... WHERE id = :id")`.
- Never interpolate variables into SQL strings.
- Never use string concatenation to build queries.

**Multi-tenant systems**
- Every database call is preceded by the appropriate tenant context (`SET LOCAL app.tenant_id = :tid` or equivalent RLS setup).
- No query executes without a tenant context in multi-tenant code paths.

**Async Redis**
- Redis is accessed only in `async def` functions using `redis.asyncio`.
- Never import or call the synchronous redis client in async code paths.

**Authorization**
- Every new route handler enforces authorization (role check, JWT validation, or equivalent).
- Authorization is never deferred to "we'll add it later."

**PII policy**
- No PII in log messages, span attributes, or metrics.
- Where identifiers must be logged, use hashes (SHA-256 or equivalent).
- This applies to all observability — logs, traces, and metrics.

**Credentials**
- No credentials, API keys, or secrets in source code.
- Use environment variables. Document required env vars in `docs/ARCHITECTURE.md` under Runtime Contract.

**Tracing**
- Shared tracing module: one `get_tracer()` function, imported everywhere.
- No inline noop span implementations scattered across files.
- All spans use the shared module.

**CI**
- CI must pass before any PR is merged.
- No exceptions. No "merge now, fix CI later."

---

## 7. Commit Discipline

### One Logical Change Per Commit

If a task involves a database migration, a service implementation, and tests, that is three commits — not one. Split at the boundary of logical changes, not at the boundary of files.

### Commit Message Format

```
type(scope): short description

Optional body: explain the why, not the what. The diff shows the what.
```

Types:
- `feat` — new feature
- `fix` — bug fix
- `refactor` — restructuring without behavior change
- `test` — adding or fixing tests
- `docs` — documentation only
- `chore` — maintenance (deps, config, CI)
- `perf` — performance improvement
- `security` — security fix

### What Not to Include in Commits

- No `Co-Authored-By` lines from AI agents
- No secrets or credentials
- No TODO comments without a task reference (`# TODO: see T{NN}`)
- No commented-out code
- No `print()` debugging statements left in production code

---

## 8. Token Efficiency Strategy

Token efficiency is not about being cheap with the API. It is about keeping agent context windows clean so that agents produce accurate outputs.

### Primary Strategies

**Subagents for heavy tasks**
Any task that requires reading more than 5 files, or produces more than approximately 2,000 lines of output, should run in a subagent. Subagents have fresh context windows — they do not carry the accumulated context of the orchestrator session.

**CODEX_PROMPT.md as session state**
`CODEX_PROMPT.md` is the zero-overhead session resumption mechanism. Any new session starts by reading this file. There is no need to re-read the entire codebase to know where you are.

**Selective reads**
Always: `grep` first to find the relevant lines, then read only those lines. Do not `cat` entire files to find one function.

**Compact before large tasks**
Run `/compact` before starting a deep review cycle or a large refactor. This condenses accumulated context without losing the active state.

**Parallel agents for independent work**
META and ARCH reviews can run as parallel subagents. Independent tasks within a phase can run as parallel subagents if there are no data dependencies between them.

**Precise Codex prompts**
The orchestrator prompt to a Codex agent must list exact files to read, exact files to modify, and the expected return format. Vague prompts cause agents to explore broadly, consuming tokens on files that are not relevant.

**Budget-aware exploration**
For AI/model tasks, broad repo reads, subagent fan-out, retry loops, and model
escalation must stay within the declared budget boundary. If the next step would
exceed the per-task or per-run budget, stop for approval instead of trying to
"finish anyway."

---

## 9. Forbidden Actions

The following actions are never permitted without explicit documented exception:

| Action | Why Forbidden |
|--------|---------------|
| String interpolation in SQL | SQL injection risk; parameterized queries are non-negotiable |
| Session-level `SET` in multi-tenant systems | Leaks tenant context across requests; use `SET LOCAL` |
| Skipping pre-task baseline capture | Cannot verify that implementation did not break existing tests |
| Self-closing review findings without code verification | Findings are closed by reading the code, not by asserting the code was fixed |
| Modifying `IMPLEMENTATION_CONTRACT.md` without an ADR | The contract is immutable; changes require architectural review |
| Deferring CI setup past Phase 1 | Every commit after Phase 1 must be CI-verified |
| Running tests without capturing the pre-change baseline | Baseline comparison is the primary correctness signal |
| Merging a PR with failing CI | The CI gate exists for this reason |
| Committing credentials or secrets | Irreversible exposure risk |

If any of these occur, they must be surfaced as P1 findings in the next review cycle. They are not waived retroactively.

---

## 10. Documentation Set

The documentation set is mode-scoped. Standard and Strict projects maintain the
full set below. Lean projects keep the required Lean artifacts from
`docs/adoption_modes.md` and add the rest only when the project risk or context
volume justifies them.

| Document | Path | Role | Mutability |
|----------|------|------|------------|
| Architecture | `docs/ARCHITECTURE.md` | Problem fit, adoption reality boundaries, system design, component table, data flows, runtime contract | Standard/Strict required; Lean required when architecture is non-trivial |
| Specification | `docs/spec.md` | Feature specification and acceptance criteria | Standard/Strict required; Lean optional for small task sets |
| Task graph | `docs/tasks.md` | Authoritative task contracts — the ground truth for what agents implement | Append-only for completed tasks; active tasks updated as needed |
| Session handoff | `docs/CODEX_PROMPT.md` or `AGENTS.md` | Current baseline, Fix Queue, open findings, next task | Required in all modes; updated before work resumes |
| Implementation contract | `docs/IMPLEMENTATION_CONTRACT.md` | Implementation rules and boundaries | Contract-lite allowed in Lean; full immutable contract in Standard/Strict |
| Review cycle reports | `docs/audit/CYCLE{N}_REVIEW.md` | Phase-by-phase review findings | Standard/Strict required at phase/risk boundaries |
| ADRs | `docs/adr/ADR{NNN}.md` | Architectural Decision Records | Required when architectural decisions change |
| Dev standards | `docs/dev-standards.md` | Code style, test strategy, observability conventions | Optional in Lean; useful when conventions are non-trivial |

### CODEX_PROMPT.md — Required Fields

Every version of `CODEX_PROMPT.md` must contain:

```markdown
## Current State
- Phase: {N}
- Baseline: {N} passing tests
- Ruff: clean | N issues
- Last CI: green | red

## Next Task
{T-NN: task name}

## Fix Queue
{list of deferred items, or "empty"}

## Open Findings
{list of P1/P2 findings from last review cycle, or "none"}

## Completed Tasks
{sequential list}
```

### tasks.md — Task Contract Format

Each task in `tasks.md` must specify:

```markdown
## T{NN}: {Task Name}

Owner: codex
Phase: {N}
Depends-On: T{XX}, T{YY}

### Objective
{One-paragraph description of what this task accomplishes}

### Acceptance Criteria
- [ ] {Specific, testable criterion}
- [ ] {Specific, testable criterion}

### Files
- Create: {list}
- Modify: {list}

### Notes
{Implementation hints, interface contracts, edge cases to handle}
```

Vague acceptance criteria produce vague implementations. "The endpoint works" is not an acceptance criterion. "GET /items returns 200 with `{"items": [...]}` when the tenant has items, 200 with `{"items": []}` when empty, and 404 when the tenant does not exist" is an acceptance criterion.

### Optional Skills

Optional, opt-in capabilities layered on the playbook live in
`reference/optional_skills.md`. Each skill follows the format in
`templates/skills/SKILL_INTERFACE.md`. Skills extend the workflow without
modifying canonical artifacts; they produce retrieval surfaces, finding
reports, or proposed task drafts that flow through normal Codex implementation
and review channels. A skill never overrides this section,
`IMPLEMENTATION_CONTRACT.md`, ADRs, `ARCHITECTURE.md`, `spec.md`, `tasks.md`,
or `CODEX_PROMPT.md`.

External skills have an additional trust gate. Before a third-party or
cross-project skill enters the agent context, use
`docs/external_skill_security_policy.md` and record trust evidence unless the
skill is instruction-only, project-local, and low-risk.

---

## 11. Known Gaps — v2 Roadmap

This section documents what the workflow does **not yet solve**. These are real limitations, not theoretical ones. They are documented here so future contributors know what is missing and why, rather than discovering it mid-project.

Each gap includes: what is missing, what impact it has, and the minimum viable addition that would close it.

---

### GAP-1: No Formal Multi-Provider / Fallback Execution Layer

**What is missing:** The playbook now documents model selection and workload-level routing, but it still lacks a formal provider-agnostic execution layer. Fallbacks, provider failover, and automatic cross-provider routing are not first-class runtime features.

**Impact:** Medium. Teams can choose different models and distribute work operationally, but provider outages or model-family saturation still require manual switching.

**v2 addition:**
- provider-agnostic execution adapter for orchestrated agents
- explicit fallback routing when the primary model family is unavailable or saturated
- optional cross-provider verification for high-risk review paths

---

### GAP-2: No Zero-Config Provider SDK Auto-Instrumentation

**Current status:** The playbook now includes model strategy, cost budget
guardrails, AI cost architecture, router/cascade eval gates, prompt-cache layout
rules, `templates/COST_BUDGET.md`, `templates/COST_ARCHITECTURE.md`,
`templates/ROUTER_EVAL.md`, and Orchestrator/Validator checks for missing
budgets, missing architecture, router eval gaps, and cost drift. It also
includes a provider-agnostic JSONL telemetry contract and `tools/cost_rollup.py`
for rollups and threshold checks. `templates/cost_adapters/python/telemetry_adapter.py`
now provides a provider-neutral starter adapter that downstream projects can
place at their provider boundary.

**Impact:** Low. Teams can define budgets, require approval, record telemetry,
and run CI threshold checks. They still need to route provider/gateway calls
through a project-owned module.

**Remaining optional addition:**
- provider-specific wrappers for a known runtime/provider layer
- optional gateway exporters for Braintrust, Maxim, TrueFoundry, OpenTelemetry,
  and provider usage APIs
- phase cost summary in CONSOLIDATED review output sourced from
  `reports/ai_cost_rollup.md`

Do not add hidden monkey-patching as the default. Explicit provider boundaries
are easier to test, review, and cost-gate.

---

### GAP-3: Security Review Not Formalized as a Separate Layer

**What is missing:** Security checks are embedded in the CODE review agent (Tier 2) and the Light review checklist (Tier 1). There is no dedicated security review agent, no formal threat model document, and no security-specific audit index.

**Impact:** High for production systems. Security findings are mixed with quality findings in REVIEW_REPORT.md. A reviewer optimizing for code quality may miss a subtle auth bypass.

**v2 addition:**
- `docs/THREAT_MODEL.md` — formal threat model (assets, threat actors, attack vectors, mitigations)
- PROMPT_SECURITY agent in the deep review pipeline: focused exclusively on auth, injection, data leakage, privilege escalation, and secrets
- Security audit index: `docs/audit/SECURITY_AUDIT.md` — one row per security finding per cycle
- Security gate in phase gate criteria: all P1 security findings resolved before gate passes

---

### GAP-4: No Performance / Load Testing Integration

**What is missing:** The workflow requires functional tests (pytest) and lint (ruff). It has no performance gate — no load test suite, no latency SLA verification, no memory/CPU regression detection.

**Impact:** Low in Phases 1–3 (correctness matters more than performance). High in Phase 6+ when the system handles real traffic.

**v2 addition:**
- Load test suite (Locust or k6) in `load_tests/`
- Baseline performance metrics stored in CODEX_PROMPT.md (e.g., `p95_latency_ms: 180`)
- Performance gate in phase gate criteria (Phase 6+): p95 latency must not regress by more than 20% vs. baseline
- Performance findings in REVIEW_REPORT.md if regression detected

---

### GAP-5: No Production Incident Integration

**What is missing:** The workflow is entirely development-focused. There is no formal path for a production incident to enter the development loop. There is no hot-fix process, no post-deployment health check, and no incident-to-task conversion.

**Impact:** High for live systems. When production breaks, the team needs a fast path that bypasses the normal phase gate process without abandoning quality controls.

**v2 addition:**
- Hot-fix task type in tasks.md: `Type: hotfix`, bypasses strategy review and deep review, triggers light review only
- Incident template: `docs/incidents/INC-{NNN}.md` — what broke, what was the impact, root cause, task created
- Post-deploy smoke test in CI: a minimal health check run after deploy, result logged to CODEX_PROMPT.md
- Incident-to-task conversion: each incident produces exactly one task entry in tasks.md

---

### GAP-6: Advanced Quality Metrics (Coverage, Complexity)

**What is missing:** The workflow tracks test count and finding severity. It does not track test coverage percentage, code complexity (cyclomatic, cognitive), or documentation coverage.

**Impact:** Low. Test count is a reasonable proxy for quality in early phases. In later phases, a project can have 200 passing tests with 40% coverage — the tests are not representative.

**v2 addition:**
- Coverage gate in CI: `pytest --cov=app --cov-fail-under=80`
- Coverage trend in CODEX_PROMPT.md: `Coverage: 73% (+2% vs. last phase)`
- Complexity budget in ARCH review: "no function with cyclomatic complexity > 15 without documented justification"

---

### Summary Table

| Gap | Severity | Effort to Close | Priority |
|-----|----------|-----------------|----------|
| GAP-1: Single-model dependency | Medium | High (orchestrator redesign) | v2 |
| GAP-2: No zero-config provider SDK auto-instrumentation | Low | Low/Medium (provider-specific wrappers/exporters) | optional |
| GAP-3: Security not formalized | High | Medium (new agent + threat model) | v2 priority |
| GAP-4: No performance testing | Low→High | Medium (load test suite + gate) | Phase 6+ |
| GAP-5: No production integration | High | Medium (incident template + hotfix path) | pre-launch |
| GAP-6: No coverage/complexity metrics | Low | Low (pytest-cov + CI flag) | v2 |

**v2 priority order:** GAP-3 (security formalization) → GAP-5 (production integration) → GAP-6 (coverage) → GAP-4 (performance testing) → GAP-1 (multi-model). GAP-2 is now optional provider-specific work, not a base playbook blocker.

_This section is updated at each major version of the playbook. Gaps that are closed move to the changelog._

---

## 12. Observability

Observability operates at three independent layers. Each layer addresses a different audience and a different failure mode. All three are required; none replaces the others.

---

### Layer 1: Process observability — Claude Code hooks

Hooks execute at the shell process level, independent of LLM decisions. They enforce the hardest-to-enforce rules and provide an independent audit trail.

| Hook event | File | What it does |
|-----------|------|-------------|
| `PreToolUse(Write\|Edit\|MultiEdit)` | `hooks/guard_files.sh` | Blocks writes to `docs/IMPLEMENTATION_CONTRACT.md`, `prompts/ORCHESTRATOR.md`, and `docs/audit/AUDIT_INDEX.md`. Exit 2 stops the tool and feeds the reason back to the Orchestrator. |
| `PostToolUse(Bash)` | `hooks/log_bash.sh` | Appends every Bash command and its exit code to `docs/hooks_log.txt`, tagged with `[TASK:T##]` when `CURRENT_TASK` env var is set by the orchestrator's Execute block. For `codex exec` invocations, also extracts and logs `IMPLEMENTATION_RESULT: DONE\|BLOCKED`. Async — does not slow the Orchestrator. |
| `Stop` | `hooks/save_checkpoint.sh` | Writes active task, Fix Queue size, and timestamp to `/tmp/orchestrator_checkpoint.md` whenever the Claude Code session ends. If `NOTIFICATION_TOKEN` and `NOTIFICATION_TARGET` env vars are set and `SILENT` ≠ 1, also sends a brief resume summary to the configured notification channel. Set `SILENT=1` for automated or cron-driven sessions to suppress delivery while still writing the checkpoint file. |

**Activation** (per project, not in this template repo):
1. Copy `hooks/` from the playbook to your project root.
2. Copy `templates/.claude/settings.json` to `.claude/settings.json` in your project root.
3. Make scripts executable: `chmod +x hooks/*.sh`
4. Verify: Claude Code will now block writes to protected files and log all Bash commands.

Override the protected file list via `PLAYBOOK_PROTECTED_FILES` env var (colon-separated paths). Override the log path via `PLAYBOOK_HOOKS_LOG`.

Per-session env vars:

| Variable | Hook | Effect |
|----------|------|--------|
| `CURRENT_TASK=T07` | `log_bash.sh` | Tags every log line with the active task ID — set this in the orchestrator's Execute block before each `codex exec` call |
| `SILENT=1` | `save_checkpoint.sh` | Suppresses session-end notification; checkpoint file is still written — use for cron or automated sessions |
| `NOTIFICATION_TOKEN=<bot_token>` | `save_checkpoint.sh` | Telegram bot token for session-end push — omit to disable |
| `NOTIFICATION_TARGET=<chat_id>` | `save_checkpoint.sh` | Telegram chat ID for session-end push — omit to disable |

---

### Layer 2: Production system observability

Rules are enforced through `docs/IMPLEMENTATION_CONTRACT.md §Observability` and reviewed at every deep review cycle via `docs/audit/PROMPT_2_CODE.md` checks OBS-1..3.

| Rule | What is required | Review check | Severity |
|------|-----------------|-------------|---------|
| OBS-1 | Every external call (DB, Redis, HTTP, LLM) wrapped in a span with `trace_id` + `operation_name` | OBS-1 in CODE review | P2 |
| OBS-2 | Success/error counter + latency histogram per external call type; AI-specific metrics when profile is ON | OBS-2 in CODE review | P2 |
| OBS-3 | `GET /health` returns `{"status": "ok"}`; no PII; no auth required | OBS-3 in CODE review | P1 |

The observability stack (OTel, statsd, Prometheus, CloudWatch) is a project-level decision declared once in `docs/ARCHITECTURE.md §Observability` and used consistently. The playbook does not mandate a specific tool.

---

### Layer 3: AI quality evaluation

Evaluation is enforced by the Orchestrator as **Step 3.5** after every task with a capability tag. CI enforces evaluation regression via the commented eval steps in `ci/ci.yml`.

| Mechanism | When it runs | What it checks |
|-----------|-------------|---------------|
| Step 3.5 (Orchestrator) | After every capability-tagged task | Did Codex update the evaluation artifact? Are Eval Source and Date present? |
| Regression threshold check (Step 3.5) | After confirmed evaluation | Primary metric drop vs. baseline: >15% → P0 (Stop-Ship); >5% → P1; ≤5% → no finding |
| OBS-2 check (CODE review) | Every deep review cycle | AI-path metrics present in code (not just in eval artifact) |
| CI eval step | Every PR (when activated) | Automated regression gate: fails CI if metric drops below stored baseline |

**Regression threshold defaults:** 15% (P0) / 5% (P1). Set explicit thresholds in `docs/CODEX_PROMPT.md §Evaluation State §Regression Thresholds` to override. A missing `§Regression Thresholds` field generates a P2 reminder.

The evaluation artifact per profile:
- RAG → `docs/retrieval_eval.md`
- Tool-Use → `docs/tool_eval.md`
- Agentic → `docs/agent_eval.md`
- Planning → `docs/plan_eval.md`

Each artifact tracks: current metrics, baseline row, regression notes, eval source, date, and corpus version (RAG only).
