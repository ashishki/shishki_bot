# Runtime Verification Protocol

## Purpose

Prevent claimed-but-not-applied changes, hidden state drift, and silent
corruption. This is a playbook-native protocol inspired by Mythos Router's
Strict Write Discipline, but it does not require Mythos.

## When Required

Use this protocol for:

- tasks with `Execution-Mode: heavy`
- tasks touching command surfaces, CI, package scripts, migrations, auth,
  secrets, retrieval indexes, agent loops, tool schemas, or compliance controls
- tasks where an agent claims file edits that the reviewer cannot cheaply infer
  from the final diff
- any correction turn after a failed implementation

For routine low-risk edits, the shortened version is acceptable: `git diff`,
tests run, and changed-file list.

## Protocol

1. Capture intent:
   - task id
   - operation type
   - claimed files
   - expected tests or evals
2. Capture before state:
   - git branch and commit
   - file existence
   - SHA-256 hash for existing files when risk warrants it
3. Apply the change through the implementer.
4. Capture after state:
   - `git diff --stat`
   - per-file existence and hash for claimed files
   - test/eval commands and status
5. Compare intent to reality:
   - claimed file missing -> failed
   - claimed mutation has no diff and no documented no-op reason -> failed
   - task-scope file changed without explanation -> review finding
   - tests not run -> incomplete
6. Record the verification result in the implementation notes, evidence index,
   or review report when the task is risky.

## Runtime Verification Record

Reusable template: `templates/RUNTIME_VERIFICATION_RECORD.md`.

```yaml
type: runtime_verification
task_id: T-123
operation: file_edit
git:
  branch: feature/example
  before_commit: 0123456789abcdef
  after_commit: fedcba9876543210
claimed_files:
  - path: src/example.py
    operation: modify
    before_hash: sha256:...
    after_hash: sha256:...
    diff_verified: true
  - path: tests/test_example.py
    operation: create
    before_hash: null
    after_hash: sha256:...
    diff_verified: true
tests_run:
  - name: unit
    command: python -m pytest tests/test_example.py -q
    status: passed
verification_status: passed
failures: []
notes:
  - "No files outside task scope changed."
```

## Failure Report

```yaml
type: runtime_verification
task_id: T-123
operation: file_edit
verification_status: failed
failures:
  - kind: claimed_file_missing
    path: src/example.py
    detail: "Agent claimed MODIFY, but file does not exist."
  - kind: test_not_run
    command: python -m pytest tests/test_example.py -q
    detail: "Completion claim included test pass, but no command output was provided."
next_action: correction_turn
correction_attempt: 1
max_correction_attempts: 2
```

## Completion Rule

No agent completion is accepted without state evidence. If the evidence is
absent, the result is `BLOCKED` or a review finding, not `DONE`.
