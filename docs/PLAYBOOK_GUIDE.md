# Choose practices for the current task

Read the task and project contract first. Choose from actual behavior and scope,
not keywords or the repository name. State your selection briefly. A prose-only
change uses its relevant checks; it does not activate UI or RAG practices.

Only enabled procedures are copied locally. For another relevant practice, use the
pinned source checkout recorded in `.playbook/connection.json`:

```text
python /path/to/playbook/tools/playbook.py practices --show ui
python /path/to/playbook/tools/playbook.py practices --root . --enable ui --apply
```

Loading instructions grants no new access, installation, spend or deployment authority.
Keep existing approvals; record unavailable live checks as NOT_RUN. Never load the
entire library for a small task. Optional procedures are not prerequisites by name.

| Practice | Apply when | Skip when | Local |
|---|---|---|---|
| task-and-proof | Every implementation or behavior change. | Pure discussion with no implementation. | enabled |
| design | A change crosses component boundaries, alters persisted/API contracts, or the project declares compact_design/designed_slices. | A bounded local fix with no contract or architecture change. | on demand |
| review | The project requires review, a significant boundary is reached, or the user asks for independent review. | A trivial edit for which the project requires no review. | on demand |
| ui | The task changes a rendered interface or user interaction. | Backend-only or prose-only changes without a UI effect. | on demand |
| rag | The change affects retrieval, indexing, chunking, grounding, citations or answer/no-answer behavior. | An unrelated task in a repository that happens to contain RAG. | on demand |
| privacy-design | The task requests design/review of personal-data boundaries in LLM/RAG or tool output. | Generic security work, unrelated LLM use, or direct processing of live personal data. | on demand |
| cost | The task introduces material model usage, retries, fan-out or a routing/caching decision. | No model calls or a documentation-only change. | on demand |
| clarify | A missing business rule or technical decision blocks the next correct implementation step. | The answer follows from the repository or a reasonable reversible choice. | on demand |
| understand-change | The user needs to understand a PR/revision range or decide whether to merge a substantive change. | A routine code edit without a change-analysis request or decision. | on demand |
| heavy-checks | Heavy tests/builds compete for measured resources and the existing heavy CLI is available. | Ordinary fast commands or an unverified host/tool installation. | on demand |
| external-tools | The task adds or changes an external skill, MCP/tool integration or its authority. | Using an already approved tool within existing scope. | on demand |
| research | A consequential design decision requires information missing from the repository. | The repository already answers the question. | on demand |
| simplify | The user asks to simplify or review complexity, or a demonstrated duplication blocks maintainability. | Speculative refactoring during an unrelated fix. | on demand |
| recover | A command fails repeatedly, work is interrupted or an external action has an unknown outcome. | A healthy task with no recovery need. | on demand |
| handoff | Ending a task/session or resuming work in a fresh session. | No project work occurred. | enabled |
| context | A long task or review needs a bounded packet of current project context. | The task is already clear from a few local files. | on demand |
| test-quality | A regression test can pass without proving the behavior, or acceptance requires stronger independent cases. | A straightforward check already reproduces and verifies the requested behavior. | on demand |
| autonomous-runtime | The project introduces scheduled or event-triggered autonomous actions in a real environment. | Interactive local development or a script with no autonomous execution requirement. | on demand |

## task-and-proof

Read the current task and contract; state acceptance, run meaningful checks, record results and the next step. Use the existing project verifier.

- [docs/testing/test_first_protocol.md](../.playbook/library/docs/testing/test_first_protocol.md)
- [docs/runtime_verification_protocol.md](../.playbook/library/docs/runtime_verification_protocol.md)

## handoff

Update the existing task/state convention with results, open findings and next step. Reconcile it with Git when resuming.

- [docs/workflow_continuity_retrofit.md](../.playbook/library/docs/workflow_continuity_retrofit.md)
