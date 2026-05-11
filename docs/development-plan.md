# Development Plan

This plan defines how context-eval should evolve using a combined
Spec-Driven Development and Test-Driven Development workflow.

SDD keeps each phase tied to an explicit product contract before code changes.
TDD keeps implementation honest by requiring failing or expanded tests before
behavior is considered complete.

## Development Method

Every feature phase follows the same loop:

1. Spec: update the relevant document in `docs/` with the user-facing contract,
   accepted inputs, outputs, edge cases, and non-goals.
2. Tests: add or update tests that encode the contract before implementation is
   treated as complete.
3. Implementation: make the smallest code change that satisfies the tests and
   preserves existing behavior.
4. Verification: run the phase acceptance commands and inspect generated
   artifacts when the behavior is file or report oriented.
5. Documentation: update README or examples only when the user workflow changes.

Phase work should not introduce LLM judges, hosted or multi-user web
dashboards, issue mining, or real network isolation unless a later spec
explicitly changes the project scope. Local-only web or visual interfaces are
in scope when they help users configure runs or inspect local evaluation data.

## Phase 0: Baseline Stewardship

Status: complete, with ongoing maintenance.

### Requirements

- Keep the runtime Python package separate from vendored maintainer tooling.
- Keep active Codex configuration opt-in.
- Keep user-facing docs focused on context-eval, not the imported skill library.
- Preserve the MVP contract: local Git repos, YAML config/tasks, variants,
  overlays, command-template agents, JSONL results, Markdown reports, and no
  automatic commits.

### Changes

- Runtime code stays under `context_eval/`.
- Vendored development skills stay under `.agents/`, `.codex/skills/`,
  `openspec/`, and `scripts/`.
- Active `.codex/config.toml` remains ignored; maintainers can copy
  `.codex/config.example.toml` locally.
- `docs/skill-hub-import.md` remains the only skill-hub provenance document.

### Test Plan

- `python -m pytest`
- `context-eval validate-config --config examples/basic/context-eval.yaml`
- `powershell -ExecutionPolicy Bypass -File scripts\validate-skills.ps1 -SkipExternal`

### Acceptance Criteria

- No upstream skill-hub `AGENTS.md` or `README*` is tracked.
- No active `.codex/config.toml` is tracked.
- Package discovery only includes `context_eval*`.
- User docs remain readable without knowing skill-hub internals.

## Phase 1: Core Runner Correctness

Status: partially complete; finish before adding broad features.

### Requirements

- A run must produce stable, versioned, machine-readable results.
- A case patch must represent agent changes relative to the selected variant,
  not the overlay itself.
- Failures must be explicit and recoverable at task plus variant granularity.
- Workspaces must be isolated and safe to retain or clean up.
- Git commands must fail loudly enough for users to debug repo/ref/worktree
  problems.

### Changes

- Keep `schema_version`, `context_eval_version`, `config_hash`, `task_hash`, and
  `variant_hash` in each JSONL row.
- Add a unique-run-directory guard so two runs in the same second never collide.
- Record Git workspace preparation failures with a specific status or structured
  error code.
- Add explicit result fields for `workspace_retained` and `cleanup_status`.
- Keep overlay baseline logic in `context_eval/evaluators/diff.py`.

### Test Plan

- Unit tests for hash stability and hash exclusions.
- Runner integration tests for:
  - completed run with validation pass
  - validation failure
  - overlay failure
  - missing repo ref
  - agent timeout
  - cleanup success and cleanup failure
  - empty patch after successful no-op agent

### Acceptance Criteria

- `python -m pytest` passes with runner integration coverage.
- `results.jsonl` can be parsed line by line with `CaseResult`.
- Overlay files do not appear in patch output unless the agent changes them
  after the overlay baseline is created.
- Timeout and agent failure cases continue to the next task and variant.

## Phase 2: Configuration And Task Spec Maturity

Status: planned.

### Requirements

- Users should be able to validate a config without accidentally running an
  agent or validation command.
- Config errors should point to the faulty field and file.
- Task files should support enough metadata for filtering and reporting without
  becoming a benchmark format.
- Path behavior must be predictable across Windows, macOS, and Linux.

### Changes

- Expand `docs/configuration.md` with a formal field reference.
- Expand `docs/task-format.md` with a formal field reference and examples.
- Add `context-eval validate-config --strict` for stronger local checks:
  repo is a Git repository, `base_ref` resolves, overlay targets are safe, and
  task IDs are filename-safe.
- Add task filters:
  - `--task-id`
  - `--category`
  - `--difficulty`
- Add config-level defaults for validation command timeout when needed.

### Test Plan

- Pydantic model tests for invalid overlay targets, duplicate tasks, empty
  prompts, and unknown variants.
- CLI tests for strict validation success/failure.
- Path-resolution tests for config-relative paths and explicit task overrides.

### Acceptance Criteria

- Invalid config and task files fail before any workspace is created.
- Error messages include enough path/field context for a user to fix YAML.
- Filtering selects the expected task set without mutating loaded config.

## Phase 3: User Workflow Usability

Status: planned.

### Requirements

- A new user should be able to bootstrap a config and run a dry check quickly.
- Users should understand what will run before paying agent or test cost.
- Existing examples should demonstrate a realistic repository workflow without
  relying on external services.

### Changes

- Add `context-eval init` to generate:
  - `context-eval.yaml`
  - `tasks.yaml`
  - `contexts/baseline/AGENTS.md`
  - `contexts/experiment/AGENTS.md`
- Add `context-eval run --dry-run` to print the task x variant matrix, resolved
  repo refs, overlay operations, prompt file paths, and validation commands.
- Add a local fixture repository under `examples/fixture-repo/` for a complete
  self-contained demo.
- Improve README quickstart to use the fixture repo rather than the context-eval
  repository itself.

### Test Plan

- CLI tests for `init` generated files.
- CLI tests for `--dry-run` output and zero side effects.
- Smoke test that runs the fixture example end to end.

### Acceptance Criteria

- A fresh clone can run the documented example without external repositories.
- `--dry-run` creates no workspace, patch, or result file.
- Generated config validates without manual editing except repo path and agent
  command.

## Phase 4: Execution Control And Reproducibility

Status: planned.

### Requirements

- Users need controlled repetition because coding agents can be nondeterministic.
- Users need bounded execution when evaluating many tasks and variants.
- Parallel execution must not corrupt workspaces or result files.
- Cleanup policy should support debugging without accumulating large run dirs.

### Changes

- Add repeated trials:
  - `--trials N`
  - `trial_index`
  - `case_id`
- Add bounded parallelism:
  - `--jobs N`
  - result writing through a single append-safe writer
- Add cleanup policies:
  - `never`
  - `always`
  - `successful`
  - `failed`
- Add run manifest with selected tasks, variants, trials, and effective config
  hashes.

### Test Plan

- Unit tests for case ID generation.
- Integration tests for trial result counts.
- Parallel execution tests with small deterministic agents.
- Cleanup policy tests for success and failure cases.

### Acceptance Criteria

- `tasks * variants * trials` result rows are produced exactly once.
- Parallel and serial runs produce equivalent result sets for deterministic
  agents.
- Cleanup behavior matches the selected policy.

## Phase 4.5: Agent Telemetry And Usage Accounting

Status: planned.

### Requirements

- Users should be able to compare task completion behavior across coding agents
  without treating context-eval as an absolute agent benchmark.
- runner-guaranteed metrics must be recorded for every case, even when the
  agent exposes no structured usage data.
- hook-provided metrics such as token usage and tool calling counts must be
  collected through optional adapter-level collectors.
- Existing command-template agent configs must keep working through a no-op
  collector.
- Telemetry collection must remain local-only and must not call hosted services
  or require a networked dashboard.

### Changes

- Add `docs/agent-telemetry.md` as the contract for telemetry fields,
  collector behavior, reporting, and non-goals.
- Extend `CaseResult` with a backwards-compatible normalized telemetry schema:
  `agent_duration_seconds`, `telemetry_status`, `telemetry_source`,
  `prompt_tokens`, `completion_tokens`, `total_tokens`, `reasoning_tokens`,
  `tool_call_count`, and `tool_calls_by_name`.
- Add an adapter telemetry hook interface that can prepare a per-case telemetry
  target and collect data after the command-template agent exits.
- Add a default no-op collector and a generic JSON telemetry collector for
  agents that can write local usage metadata.
- Add report, compare, inspect, and local UI aggregations for collected,
  partial, and unavailable telemetry.

### Test Plan

- Spec tests for `docs/agent-telemetry.md` and this development plan phase.
- Model tests for backwards-compatible result parsing and telemetry defaults.
- Adapter tests for the no-op collector and generic JSON telemetry collector.
- Runner integration tests for agent duration, telemetry status, token counts,
  and tool calling counts in `results.jsonl`.
- Report and CLI tests for aggregation behavior across collected, partial, and
  unavailable telemetry.

### Acceptance Criteria

- Agent telemetry contract and normalized result schema are documented and
  tested before implementation.
- `results.jsonl` remains parseable for old and new runs.
- Missing token/tool telemetry is represented explicitly, not guessed from logs.
- Do not claim absolute coding-agent capability; reports frame metrics as local
  observations for a recorded agent, task, variant, and trial configuration.
- The first implementation supports a no-op collector and a generic JSON
  telemetry collector without adding agent-specific brittle parsers.

## Phase 5: Reporting And Analysis

Status: planned.

### Requirements

- Reports should help compare context variants, not claim absolute agent skill.
- JSONL should remain the source of truth.
- Users should be able to regenerate reports and inspect summaries without
  rerunning agents.
- Users should have a local web interface or other visual interface for
  configuring evaluation environments and viewing current or historical test
  data without editing YAML or reading JSONL directly.
- The visual interface must remain local-first: it may read and write local
  config/task files and local run artifacts, but it must not require a hosted
  service, remote database, or networked dashboard backend.

### Changes

- Add `context-eval inspect-run RUN_DIR` for tabular terminal summaries.
- Add `context-eval compare RUN_DIR` for variant-oriented metrics:
  pass rate, timeout rate, agent failure rate, validation failure rate, average
  duration, average changed files, and common touched paths.
- Add result export helpers for CSV and compact JSON summary.
- Add local-only multi-agent comparison summaries and exports based on
  `docs/multi-agent-comparison.md`.
- Harden compact JSON export metadata with a stable export schema version,
  controlled export timestamp, local source file list, and case, agent,
  variant, and task counts derived only from `results.jsonl` and optional
  `run_metadata.json`.
- Improve report template readability for multiple tasks and variants.
- Add a local visualization entrypoint, such as `context-eval ui`, a generated
  static HTML report, or a terminal UI, that can:
  - configure repo path, base ref, agent command, variants, overlays, tasks, and
    validation commands;
  - validate the edited configuration before a run starts;
  - show the selected task x variant matrix before execution;
  - display current and previous run results from local `results.jsonl` and
    `run_metadata.json` files.
- Use `docs/local-ui-config-editor.md` as the contract for the local UI config
  editor, YAML export, and any future explicit local save behavior.

### Test Plan

- Report tests using synthetic JSONL fixtures.
- Export tests for deterministic CSV and compact JSON summaries from local
  artifacts.
- Export tests for compact JSON export metadata, including missing
  `run_metadata.json`, empty `results.jsonl`, and multi-agent, multi-variant,
  multi-task count behavior with controllable timestamps.
- Snapshot-style assertions for Markdown sections and key table rows.
- CLI tests for missing or malformed run directories.
- Interface tests for config editing, validation feedback, and result loading
  from local run artifacts.

### Acceptance Criteria

- Report generation works from JSONL and metadata alone.
- Low-confidence results are clearly called out.
- Aggregations are deterministic and documented.
- Multi-agent comparison is framed as local run observation, not an absolute
  coding-agent benchmark.
- A user can configure an evaluation environment through the local visual
  interface, validate it, and inspect current test data without opening YAML or
  JSONL files directly.
- The visual interface can run offline against local files and does not create
  or depend on a hosted dashboard service.

## Phase 6: Adapter And Prompt Extensibility

Status: planned.

### Requirements

- The command-template adapter remains the stable default.
- Advanced users can customize prompts without changing Python code.
- Adapter extensions must not force complex framework dependencies into the MVP.

### Changes

- Add config support for `prompt_template`.
- Add prompt rendering tests for template variables and missing fields.
- Add adapter contract docs that specify command environment, cwd, timeout,
  stdout/stderr capture, and no automatic commits.
- Consider a thin Python entrypoint adapter only if repeated command-template
  use shows real friction.

### Test Plan

- Prompt template unit tests.
- Config validation tests for missing template files.
- Adapter tests for command substitution and unknown variables.

### Acceptance Criteria

- Existing configs continue to work unchanged.
- Custom prompt templates can reproduce the default prompt.
- Missing template files fail during config validation.

## Phase 7: CI And Release Readiness

Status: planned.

### Requirements

- Contributors should get fast feedback before merge.
- Releases should be reproducible and not include local run artifacts.
- The project should declare supported Python versions and platform limits.

### Changes

- Add GitHub Actions for:
  - pytest
  - ruff
  - example config validation
  - skill validation with `-SkipExternal`
- Ensure every CI job installs the dependencies needed by the commands it runs.
- Keep `-SkipExternal` skill validation independent from maintainer-home tools
  that are not available on hosted CI runners.
- Add packaging check with `python -m build` once `build` is in dev
  dependencies.
- Add `CHANGELOG.md`.
- Add release checklist documentation.

### Test Plan

- CI workflow runs on pull requests.
- Local commands mirror CI commands.
- Build artifact contents are inspected for accidental vendored runtime data.

### Acceptance Criteria

- CI passes on Windows and Linux for Python 3.11+.
- Published package contains `context_eval` runtime and report templates, not
  run artifacts.
- Release checklist can be followed without hidden local state.

## Cross-Phase Quality Gates

Before a phase is considered complete:

- The phase spec is present in docs.
- Tests for new behavior exist and fail before implementation or clearly cover a
  bug being fixed.
- `python -m pytest` passes.
- `context-eval validate-config --config examples/basic/context-eval.yaml`
  passes.
- `powershell -ExecutionPolicy Bypass -File scripts\validate-skills.ps1 -SkipExternal`
  passes on Windows maintainer machines.
- Generated artifacts are inspected when the change affects reports, JSONL,
  prompts, patches, or workspaces.

## Near-Term Backlog Order

1. Unique run directory guard and cleanup status fields.
2. Strict config validation and task filters.
3. Self-contained fixture repo example.
4. `context-eval run --dry-run`.
5. `context-eval init`.
6. Trial support.
7. Agent telemetry contract and normalized result schema.
8. Adapter telemetry hook interface with no-op and generic JSON collectors.
9. Report/inspect commands.
10. Local visual interface for config and run data.
11. CI workflow and release checklist.
