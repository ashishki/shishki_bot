# Project Fit Guide

Use this guide before bootstrapping a project with AI Workflow Playbook. The goal
is to decide whether the playbook solves a real workflow problem, which entry
point fits, and which claims must wait for evidence.

The playbook is strongest as a governance, proof, review, and continuity layer.
It is not a product strategy substitute and not a remote execution fabric.

---

## Problem-First Entry Gate

Before selecting phases, capability profiles, or runtime tier, answer:

| Question | Required answer |
|----------|-----------------|
| Concrete operational pain | What currently breaks, stalls, costs too much, or depends on fragile human effort |
| Current workaround | How the team handles the work today without this system |
| Why current process is insufficient | Why checklists, CI, ordinary review, scripts, or manual SOPs are not enough |
| First user / operator | The role or team that will feel the improvement first |
| Adoption failure condition | What would make v1 not worth using |
| First proof metric | The smallest measurable signal that proves practical value |

If the answer is mostly "we want to use agents" or "AI should make this better",
do not start a full playbook build. Start with discovery, measurement, or a
small deterministic improvement.

---

## Adoption Reality Gate

AI adoption claims are allowed only when they are scoped and measurable.

| Claim area | Required boundary |
|------------|-------------------|
| Work AI improves | Name the specific workflow, task, or decision support surface |
| Work AI does not replace | Name the human judgment, approval, accountability, or domain expertise that remains human-owned |
| Demo-to-production evidence | Define the eval, test, operator review, or production metric needed before trust increases |
| Forbidden pre-evidence claims | List claims that must not be used in sales, planning, or demos until evidence exists |

Treat broad claims like "replaces engineers", "fully autonomous team",
"production-ready swarm", or "AI-native transformation" as invalid until the
architecture package defines exact scope, approval boundaries, and a metric that
could falsify the claim.

---

## Good Entry Points

| Entry point | Use the playbook when | Typical mode |
|-------------|-----------------------|--------------|
| Retrofit governance | Existing repo has drift, weak task contracts, unclear review gates, or lost context | Standard playbook |
| Risky migration | Auth, RLS, data migration, deletion, security boundary, or rollback risk dominates | Heavy-task mode |
| RAG / eval discipline | Retrieval quality, citations, insufficient-evidence behavior, or corpus drift must be measured | RAG profile |
| Tool safety | LLM-directed tools can mutate external state, spend money, or call unsafe actions | Tool-Use profile |
| Agent loop control | The system really needs bounded iteration, handoff, or termination logic | Agentic profile |
| Planning handoff | The system's primary output is a structured plan consumed by humans or downstream execution | Planning profile |
| Bootstrap kit | A new repo needs repeatable contracts, CI, Codex handoff, and phase gates from day one | Lean or Standard |

---

## Anti-Patterns

Do not use the full playbook when:

- there is no named current pain or user
- the main goal is an impressive demo rather than a repeatable workflow
- success is stated as "use agents" rather than a business, quality, latency,
  cost, or operational metric
- the team expects agents to replace accountable human judgment without an eval,
  approval, and rollback boundary
- a script, checklist, CI improvement, or ordinary review rule would solve the
  problem with less process
- the primary problem is distributed scheduling, durable queues, branch
  isolation, or remote execution runtime

In those cases, use the smaller tool: a discovery note, a deterministic script,
a CI gate, a review checklist, or an external runtime with the playbook as a
governance overlay.

---

## Fit Verdict

Use this short verdict before bootstrapping:

| Verdict | Meaning |
|---------|---------|
| Use as-is | Concrete pain, measurable proof, bounded workflow, and playbook governance directly apply |
| Use with heavy-task mode | The project fits, but false confidence or rollback cost is high |
| Use as governance overlay | External runtime or scheduler is needed; playbook governs contracts, proof, and review |
| Do not use yet | Pain, owner, current workaround, or proof metric is unclear |

