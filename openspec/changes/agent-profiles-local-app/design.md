## Context

context-eval is a local engineering tool for comparing context variants in real
Git repositories. The current config has one command-template agent, the runner
executes task x variant x trial, and the generated UI is static export-only.
The requested product direction needs two architectural moves: first model
coding agents as named noninteractive local profiles, then add an explicit
local app mode that can write config files and launch runs.

## Goals / Non-Goals

**Goals:**

- Keep the existing single `agent` config working.
- Add named profiles for Codex CLI, Claude Code, and custom local agents.
- Support a deterministic agent x task x variant x trial matrix.
- Introduce a local app mode with save, preflight, run, progress, and result
  workflows.
- Preserve local-only artifacts and non-leaderboard language.

**Non-Goals:**

- No hosted dashboard, remote database, shared account system, or remote run
  service.
- No automatic installation or upgrading of Codex CLI, Claude Code, or custom
  agents.
- No LLM judge, automatic commits, provider billing reconciliation, or absolute
  coding-agent ranking.
- No change to static UI safety: static HTML remains offline and cannot run
  agents.

## Decisions

1. Agent profiles come before Web UI.

   The UI cannot safely launch evaluations until profile validation, command
   rendering, matrix planning, artifact naming, and result row semantics are
   explicit. Implementing profiles first gives the Web UI a stable product
   model instead of duplicating CLI assumptions in frontend code.

2. Keep command templates as the adapter baseline.

   Codex CLI, Claude Code, and custom agents all differ in flags and local
   authentication behavior, but they can be represented by editable
   noninteractive command templates. Built-in profile kinds should provide
   presets and validation copy, not opaque SDK integrations.

3. Preserve compatibility by treating existing `agent` as a single implicit
   profile.

   Existing configs and examples should continue to run. The new `agents` map
   becomes the preferred shape for multi-agent work. Mixing `agent` and
   `agents` should fail clearly until an explicit migration rule exists.

4. Add local app mode as a separate command and runtime boundary.

   Static UI and local app mode have different safety properties. Keeping them
   separate lets static HTML remain shareable and offline while local app mode
   can intentionally write files and execute local agent commands after user
   confirmation.

5. Bind the local app to loopback and keep all data file-based.

   A small local server can expose project/config/run/artifact endpoints, but
   the source of truth remains local YAML and run artifacts. This avoids a
   database migration before the product needs one.

## Risks / Trade-offs

- Command templates can still encode interactive behavior. Mitigation: preflight
  validates variables and executable presence, docs require noninteractive
  commands, and timeouts remain mandatory.
- Agent-specific defaults may drift as external CLIs change. Mitigation:
  presets are editable and tests cover only context-eval's rendering and
  validation contract, not vendor CLI internals.
- Local app mode increases write and execution risk. Mitigation: show file
  paths before writes, require explicit run confirmation, bind to loopback, and
  reuse the existing runner.
- Multi-agent matrices can become expensive. Mitigation: expose matrix preview,
  selected profiles, jobs, trials, and case count before execution.

## Migration Plan

1. Land specs and docs for agent profiles and local app mode.
2. Implement agent profile parsing and matrix planning behind tests.
3. Update runner artifacts and reports to handle selected profiles.
4. Add a minimal local server API for config save/load, preflight, run planning,
   and artifact reads.
5. Build the first Web UI workflow on top of the API.
6. Add a no-command-line launcher only after the local app workflow is stable.

Rollback is straightforward before implementation: remove the change directory
and docs updates. After implementation, existing single-agent configs remain the
compatibility rollback path.

## Open Questions

- Which exact Codex CLI and Claude Code noninteractive templates should the
  first presets ship with?
- Should the first local app server use a Python-only stack or introduce a
  frontend build tool after the API contract is stable?
- Should a real external-agent smoke test remain manual, or be added as an
  opt-in local test marker after fake-agent local-e2e coverage is green?

