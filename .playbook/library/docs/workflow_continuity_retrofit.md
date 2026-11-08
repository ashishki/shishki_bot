# Workflow Continuity Retrofit

Date: 2026-04-07
Scope: `AI_workflow_playbook` retrofit after critical review of `milla-jovovich/mempalace`

---

## Architectural Verdict

`AI_workflow_playbook` should not become a generic AI memory framework.

It should adopt a lighter continuity model:

- canonical truth remains explicit project files
- retrieval becomes a disciplined convenience layer over those files
- the useful target is better architectural recall, evidence lookup, implementation continuity, and reviewer carry-forward
- the wrong target is a palace metaphor, generic personal memory, or any system that competes with source-of-truth docs

The right retrofit is therefore:

- `docs/DECISION_LOG.md` for decision recall
- `docs/IMPLEMENTATION_JOURNAL.md` for cross-session implementation continuity
- `docs/EVIDENCE_INDEX.md` for proof lookup when review or evaluation history grows
- task-level `Context-Refs` for scoped retrieval
- prompt and contract rules that make retrieval mandatory only when prior context materially affects correctness

---

## 1. Current-State Assessment

### What continuity already exists

- `docs/CODEX_PROMPT.md` already provides strong operational resumability: next task, baseline, findings, phase history, profile state.
- `docs/IMPLEMENTATION_CONTRACT.md` already provides immutable policy continuity.
- `docs/ARCHITECTURE.md`, ADRs, review archives, and evaluation artifacts already preserve explicit project truth.
- `docs/tasks.md` already acts as a durable execution contract with dependencies and acceptance criteria.

### Where project memory already lives

- architecture intent: `docs/ARCHITECTURE.md`
- hard rules: `docs/IMPLEMENTATION_CONTRACT.md`
- live execution state: `docs/CODEX_PROMPT.md`
- task history and review findings: `docs/audit/*`
- profile-specific proof: `docs/*_eval.md`
- code-level truth: repo source + tests + CI

### Where context is lost or expensive today

- prior decisions are scattered across architecture text, ADRs, review reports, and chat history; there is no retrieval index
- implementation rationale between commits is thin; `CODEX_PROMPT.md` tracks state, not why a change happened
- repeated findings require manual archaeology across archived reviews
- tasks have dependencies but no scoped retrieval pointers for prior evidence or decisions
- the playbook already preserves truth, but it does not yet preserve convenient recall

### What the current system already solves without memory features

- resumability of live work
- auditability of tasks and findings
- role separation and phase discipline
- evaluation and compliance artifact storage
- source-of-truth governance through explicit docs

### Stale or inconsistent points found during review

- README used broken absolute links instead of repo-relative links
- continuity language over-centered `CODEX_PROMPT.md` and under-described other retrievable artifacts
- prompts and templates had no shared terminology for decision recall, evidence lookup, or implementation journaling

---

## 2. Critical MemPalace Extraction

### Verified implementation and product facts

- local-first design: README positions MemPalace as offline and local, using ChromaDB plus local files
- layered context model: L0 identity, L1 critical facts, L2 room recall, L3 deep search
- segmentation model: wings, halls, rooms, closets used to scope retrieval
- storage model: verbatim text is kept rather than only extracted summaries
- tool surface: MCP server exposes search, taxonomy, graph, diary, and navigation tools
- extra surfaces: knowledge graph with temporal triples, agent-specific diaries, auto-save hooks, benchmark runners

### Ideas with real leverage for this playbook

- layered loading is useful when translated into workflow surfaces: current state first, targeted retrieval second, deep search only when needed
- scoped retrieval is genuinely useful; task-local context should beat global recall
- verbatim evidence preservation matters more than lossy memory summaries
- role-specific continuity has value when it improves execution quality, especially for implementer and reviewer handoff
- local-first/file-first assumptions align with this repository

### Ideas that are weakly supported or not relevant here

- benchmark claims are meaningful for conversation retrieval systems, but they do not directly validate a workflow-governance framework
- the palace metaphor is memorable but not engineering-clear for this repository
- a general agent diary per specialist is interesting, but this playbook needs project-bound execution continuity more than persona memory
- a graph-navigation layer is unnecessary unless file retrieval becomes a proven bottleneck
- AAAK compression is not needed here because the playbook already optimizes through explicit artifacts and scoped reads

### Ideas that conflict with the playbook philosophy

- any framing where "memory" competes with canonical files
- auto-saved conversational recollection as an implicit authority
- generic personal-preference storage unrelated to project execution
- memory abstractions that would blur the line between review evidence and convenient summary

---

## 3. Playbook-Native Adaptation

### What "memory" should mean here

Not chatbot memory.

It should mean: retrievable project continuity from explicit, file-backed artifacts.

### Canonical truth must remain

- `ARCHITECTURE.md`
- `IMPLEMENTATION_CONTRACT.md`
- `tasks.md`
- `CODEX_PROMPT.md`
- ADRs
- audit reports
- evaluation artifacts
- code, tests, CI

### Retrieval convenience should become

- `DECISION_LOG.md`: index of important decisions with canonical links
- `IMPLEMENTATION_JOURNAL.md`: append-only task/session handoff log
- `EVIDENCE_INDEX.md`: optional index of proof artifacts when evidence volume grows
- `Context-Refs` in tasks: task-scoped retrieval pointers

### Role-scoped context

- Strategist: retrieve prior decisions, superseded assumptions, open evidence gaps before changing architecture or decomposition
- Orchestrator: retrieve current task context from `Context-Refs`, recent journal entries, open findings, and evidence rows before dispatch
- Reviewer: retrieve prior findings and prior proof for the same boundary before issuing carry-forward verdicts

### Mandatory retrieval triggers

Retrieval should be mandatory, not optional, when a task:

- resolves or reopens a prior finding
- changes architecture, runtime, or governance boundaries
- touches auth, retrieval semantics, tool safety, agent loops, compliance, migrations, or other heavy-task surfaces
- depends on earlier tasks with non-trivial interface or policy decisions

For isolated leaf tasks with clear scope and no prior history dependency, retrieval remains optional.

---

## 4. MemPalace Idea Classification

| Classification | MemPalace idea | Playbook decision | Reason |
|----------------|----------------|-------------------|--------|
| Adopt in lighter playbook-native form | Layered context loading | Yes | Translate to: current state first, scoped task retrieval second, deep archive lookup only when needed |
| Adopt in lighter playbook-native form | Scoped retrieval by segment | Yes | Use task `Context-Refs`, Decision Log, Evidence Index, and journal sections instead of wings/rooms |
| Adopt | Verbatim evidence preservation | Yes | Keep proof in files, tests, review reports, and eval artifacts; do not collapse to summaries |
| Adopt in lighter playbook-native form | Role-specific continuity surfaces | Yes | Use implementer/reviewer/orchestrator retrieval rules, not generic agent personas |
| Defer | Knowledge graph / temporal triples | Defer | Potentially useful later for large audit histories, but unnecessary for current playbook scope |
| Reject | Palace metaphor | Reject | Memorable branding, weak engineering clarity for workflow governance |
| Reject | Generic personal memory framing | Reject | Out of scope for project execution and architecture control |
| Reject | AAAK dialect / compression layer | Reject | Adds abstraction without solving a current bottleneck in explicit file workflows |
| Reject | Benchmark-first positioning | Reject | Retrieval benchmarks do not prove governance quality or execution reliability |
| Defer | Auto-save hooks for implicit memory capture | Defer | Existing checkpoint hooks are enough; automatic context capture risks noisy authority surfaces |

---

## 5. Updated Phased Task Decomposition

### Phase 1 — Minimal continuity upgrade

- add `DECISION_LOG.md` and `IMPLEMENTATION_JOURNAL.md` templates
- add continuity/retrieval sections to architecture, contract, and code prompt templates
- add task-level `Context-Refs`
- update Strategist, Orchestrator, and validator prompts to recognize the new surfaces

Validation:

- a new project can bootstrap the continuity artifacts without changing playbook authority rules
- tasks can point to prior decisions or evidence without free-form chat recall

### Phase 2 — Evidence retrieval discipline

- add `EVIDENCE_INDEX.md` template and usage rules
- require evidence indexing for heavy tasks, active eval profiles, and recurring findings
- update review guidance so carry-forward checks look at prior evidence before re-raising issues

Validation:

- reviewers can answer "what proved this before?" without scanning the whole repo history

### Phase 3 — Retrofit / migration guidance

- teach retrofit users how to initialize decision log and journal from existing docs instead of reconstructing full history
- tell users not to backfill everything; start from active architecture, active findings, and the next real task
- document when to omit `EVIDENCE_INDEX.md` in lean projects

Validation:

- existing projects can adopt the continuity model incrementally
- migration overhead stays low for solo builders and small teams

### Deferred future work

- optional tooling to generate or refresh evidence index rows from review/eval artifacts
- optional structured retrieval helper scripts
- no graph layer, semantic memory substrate, or autonomous memory mining until real repo-scale pain proves the need

---

## 6. Next Execution Step

Recommended first retrofit phase:

1. generate `docs/DECISION_LOG.md` and `docs/IMPLEMENTATION_JOURNAL.md` in target projects
2. add `Context-Refs` to tasks that touch architecture, findings, or risky boundaries
3. teach the Orchestrator to read only those references plus recent journal/evidence rows before dispatching Codex

This gives the playbook the useful part of "memory" immediately: scoped recall with explicit authority boundaries.
