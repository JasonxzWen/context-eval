## Why

context-eval currently has enough local artifact and static UI foundation to
compare completed runs, but non-technical users still have to edit YAML and run
commands manually. The next product step is to make noninteractive coding-agent
profiles explicit first, then build a local web app that can configure, launch,
monitor, and inspect evaluations without turning the project into a hosted
benchmark service.

## What Changes

- Add a planned first-class agent profile model for Codex CLI, Claude Code, and
  custom local commands such as `coco -p {prompt_file}`.
- Expand the planned execution matrix from task x variant x trial to agent x
  task x variant x trial while preserving local artifacts and non-benchmark
  language.
- Define a separate local app mode that can save config, run preflight checks,
  start local evaluations, stream progress, and inspect results.
- Preserve static UI mode as offline, self-contained, and safe for export-only
  config editing and artifact viewing.
- Update the development plan so agent profiles precede the full Web UI.

## Capabilities

### New Capabilities

- `agent-profiles`: Noninteractive local coding-agent profiles, command
  templates, compatibility with the existing `agent` config, and multi-agent
  matrix execution.
- `local-app-workflow`: Local server/app mode for visual configuration,
  preflight, run orchestration, result review, and no-command-line product
  workflow.

### Modified Capabilities

- None. The repository does not yet have archived OpenSpec capability specs.

## Impact

- Runtime model: future changes will extend `ContextEvalConfig` with named
  agent profiles while keeping the single-agent shape compatible.
- Runner: future changes will plan and execute cases by selected agent profile.
- UI/API: future changes will introduce an explicit local app mode separate
  from static HTML generation.
- Docs/tests: `docs/agent-profiles.md`, `docs/local-app-workflow.md`, and
  `docs/development-plan.md` become the source contracts for the next product
  expansion.

