# External Skill Security Policy

## Purpose

External agent skills are supply-chain artifacts. They can contain instructions,
code, scripts, references, assets, tool schemas, and metadata that influence an
agent with the agent's own permissions.

This policy governs third-party or cross-project skills before they are
installed, enabled, updated, or shared broadly. It covers Claude Code, Codex,
Cursor, Gemini CLI, MCP-adjacent skill bundles, and any similar skill package.

Internal project-local instructions may use the lightweight path only when they
are instruction-only, reviewed in the same repo, and do not add executable
scripts, network calls, environment access, file writes, MCP servers, or tool
permissions.

## External Basis

This policy adapts the NVIDIA SkillSpector trust pipeline:

- SkillSpector scans skill directories, Git URLs, zip files, directories, and
  single `SKILL.md` files; it supports static analysis and optional LLM
  semantic analysis. Source: https://github.com/NVIDIA/SkillSpector and
  https://docs.nvidia.com/skills/scanning-agent-skills
- NVIDIA's trust pipeline separates scanning, skill cards, and signatures:
  scanning asks whether content appears safe enough; signing asks whether the
  installed artifact matches the reviewed artifact. Source:
  https://docs.nvidia.com/skills/agent-skill-trust-pipeline
- NVIDIA's signing docs state that OMS-style detached signatures verify the
  skill directory and should be checked before installation or CI use. Source:
  https://docs.nvidia.com/skills/signing-agent-skills
- The "Agent Skills in the Wild" study reports that agent skills execute with
  implicit trust and that vulnerabilities are common enough to justify mandatory
  vetting before installation. Source: https://arxiv.org/abs/2601.10338

These sources are references, not mandatory runtime dependencies. The playbook
requires the gate and evidence; SkillSpector is the recommended scanner when it
is available.

## Default Rule

Do not install or enable an external skill until a trust record exists.

Use `templates/EXTERNAL_SKILL_TRUST_RECORD.md` and store the completed record
at:

```text
docs/security/skills/{skill-name}/TRUST_RECORD.md
```

Lean projects may keep a short inline record only for instruction-only skills
with no scripts, no tool/MCP access, no network access, no environment access,
and no file writes. Anything executable or externally sourced needs the full
record.

## Trust Gate

### 1. Source and Version

Record:

- source URL
- owner or accountable maintainer
- license or terms
- exact version: tag, commit SHA, release artifact hash, or local tree hash
- install scope: project-local or global
- update policy

Project-local install is the default. Global install requires explicit human
approval and a stronger justification because it affects future unrelated
projects.

### 2. Capability Declaration

Record every declared or inferred capability:

- shell execution
- network egress
- file read/write scope
- environment variable or secret access
- MCP server/tool access
- package/dependency installation
- persistent state, cron, startup scripts, or background processes
- external API calls
- output type and side effects

Undeclared capability is a P1 unless removed or explicitly accepted. Wildcard
permissions such as `*`, `all`, `full`, or "read the project" are rejected
unless tightly scoped in an ADR or risk acceptance record.

### 3. SkillSpector Scan

Run a scan against the complete skill directory before installation:

```bash
skillspector scan ./skill-name --format markdown --output docs/security/skills/skill-name/skillspector-report.md
```

Use static-only mode when credentials or external LLM analysis are not allowed:

```bash
skillspector scan ./skill-name --no-llm --format markdown --output docs/security/skills/skill-name/skillspector-report.md
```

For CI/code-scanning integration, SARIF is preferred:

```bash
skillspector scan ./skill-name --no-llm --format sarif --output reports/skills/skill-name.sarif
```

The playbook wrapper can enforce the trust record and scanner result together:

```bash
python3 tools/skill_security_gate.py \
  --root . \
  --discover-agent-skills \
  --require-scanner \
  --sarif
```

The wrapper exits 0 when no external skills are discovered. When skills are
present, it requires `docs/security/skills/{skill-name}/TRUST_RECORD.md`, runs
SkillSpector JSON output for policy parsing, optionally writes SARIF, and fails
on missing trust records, unapproved trust records, missing source pin/signature
evidence, risk scores above threshold, `DO_NOT_INSTALL`, or unresolved
CRITICAL/HIGH findings unless the trust record explicitly records
`Critical/high risk acceptance: yes`.

If SkillSpector is unavailable, the trust record must say which alternative
checks were run and why the missing scanner is acceptable. A missing scanner is
not acceptable for high-risk executable skills.

### 4. Triage Policy

| Finding | Required action |
|---------|-----------------|
| CRITICAL or HIGH | Block install until fixed or formally accepted by a human owner |
| Hidden instructions / tool poisoning | Remove hidden content or reject the skill |
| Credential access / env harvesting | Reject unless the behavior is essential, scoped, and approved |
| Known vulnerable dependency | Upgrade, pin a fixed version, or document accepted risk |
| Description-behavior mismatch | Rewrite the description or change/remove behavior |
| MEDIUM | Review for policy impact; accept only with mitigation |
| LOW | Track if it affects permissions, dependencies, or trigger breadth |

Accepted CRITICAL/HIGH findings require a risk acceptance record linked from the
trust record. "Scanner false positive" is not enough; explain the bounded
reason.

### 5. Skill Card

Every external skill trust record must include or link a skill card with:

- one-sentence description of actual behavior
- owner/accountable team
- license or terms
- intended users and workflows
- deployment geography or environment scope
- known risks and mitigations
- output type/format and side effects
- version, release tag, signature ID, or hash
- scan report, CI link, or review evidence

The card exists so a reviewer can understand what is being accepted before
opening source code.

### 6. Signature or Integrity Verification

If a detached signature such as `skill.oms.sig` is present, verify it before
installation and record the command/output in the trust record.

If no signature exists, pin the source to a commit SHA or artifact hash. Do not
install from an unpinned branch for Standard or Strict projects.

Signing does not prove a skill is safe. It proves the installed artifact is the
one that was reviewed. Scanning and human review are still required.

### 7. Install and Runtime Controls

- Project-local install is default.
- Global install requires human approval.
- Auto-update is disabled unless the update path reruns this gate.
- The skill is enabled only for projects and sessions that need it.
- New version, changed source, changed dependency, changed permission, changed
  trigger, or changed executable file reruns the gate.
- External skills must not weaken `docs/IMPLEMENTATION_CONTRACT.md`,
  `docs/CODEX_PROMPT.md`, hooks, CI, review prompts, or cost/security gates.

## Blocked Patterns

Treat these as P0/P1 unless a human owner records explicit risk acceptance:

- hidden instructions, HTML comments, zero-width characters, or metadata that
  changes agent behavior invisibly
- prompt text that tells the agent to ignore system, developer, contract, or
  user instructions
- environment variable harvesting or credential file access
- broad filesystem enumeration
- `curl | bash`, remote script execution, obfuscated executable payloads
- `exec`, `eval`, dynamic imports, shell execution from external input
- unpinned dependencies for executable skills
- broad triggers that shadow common commands or other skills
- persistent background processes, cron jobs, startup scripts, or self-modifying
  behavior
- MCP/tool permissions that are broader than the skill's stated purpose
- description-behavior mismatch

## Review Checks

Before approval, reviewers must answer:

- Does the skill description match executable behavior?
- Are network, shell, file, environment, MCP, and tool permissions declared and
  justified?
- Are critical/high findings fixed or formally accepted?
- Is the source pinned, signed, or hashed?
- Does the trust record name install scope, update policy, and rollback/removal
  path?
- Does the skill add a new capability profile, runtime tier, or external tool
  boundary that must be reflected in architecture/tasks/contracts?

If any answer is unclear, the skill is not ready.
