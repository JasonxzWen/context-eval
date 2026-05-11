# Development Plan

This plan defines how context-eval should evolve using Spec-Driven Development
and Test-Driven Development while avoiding a PR cadence that is too small for
maintainer review.

The project has moved past its initial MVP foundation. Future work should be
planned as capability PRs: each PR owns one coherent user-facing capability,
can contain several Ralph stories, and must merge with a complete acceptance
package.

## Product Boundaries

- `context_eval/` is the runtime Python package.
- `.agents/`, `.codex/skills/`, `openspec/`, and `scripts/` are maintainer
  capability library files, not runtime package modules.
- Deleted general-purpose skill-hub documents must not be restored.
- Active `.codex/config.toml` must not be committed; maintainers can copy
  `.codex/config.example.toml` locally.
- context-eval remains a local engineering tool for comparing context variants,
  not an agent leaderboard.
- Multi-agent comparison must be based only on local `results.jsonl` and
  `run_metadata.json` artifacts, and must not claim absolute agent benchmark
  results.
- Report, export, compare, and UI aggregation must read local run artifacts.
  They must not rerun agents, scrape missing telemetry from logs, or call
  hosted services.
- The active roadmap does not include an LLM judge, hosted or multi-user web
  dashboard, issue miner, real network isolation, or automatic commits.

## Development Cadence Policy

A Ralph story is not a pull request. A Ralph story is the smallest autonomous
unit inside a capability PR. A capability PR should contain 3-6 related Ralph stories.
Those stories must share one capability boundary and can be reviewed as one
product change.

Each story still follows SDD + TDD:

1. Spec: update the relevant document in `docs/` with the contract, edge cases,
   and non-goals.
2. Tests: add or update tests that encode that contract before the
   implementation is treated as complete.
3. Implementation: make the smallest code change needed for the story.
4. Docs: update README, examples, or workflow docs when user behavior changes.
5. Verification: run the agreed quality gates and inspect generated artifacts
   when the story affects reports, exports, prompts, workspaces, or UI.

Do not open one PR per story. Open or update the PR only when the capability has
a coherent merge package: spec, tests, implementation, docs, verification. A
story can still be committed separately inside the PR so review history remains
clear.

Capability PRs should be split only when one of these is true:

- the stories have different users or different operational boundaries;
- verification would require unrelated artifact sets;
- the PR would mix runtime behavior with maintainer tooling without a shared
  acceptance contract;
- the review would exceed a coherent diff size or introduce unrelated risk.

## Capability Audit: PR #1-#17

PR #1-#4 established broad capability slices: runner/config maturity, local UI
config editing, agent telemetry, and local multi-agent comparison. Those PRs
were easier to reason about because the spec, tests, implementation, docs, and
verification all pointed at the same capability.

PR #5-#17 delivered useful work, but the cadence became too fine-grained. The
work added Markdown agent summaries, compact JSON metadata, bounded jobs,
cleanup policies, run manifests, prompt templates, package build checks,
license metadata, platform docs, artifact inspection, release-state checks,
development-plan reconciliation, and validation timeout defaults. Several of
these were good stories, but they were often promoted to separate PRs before
the surrounding capability was complete.

The strongest signal is release readiness: release readiness was split across build, license, platform, artifact inspection, and release-state PRs.
Those changes should have been reviewed as one release automation and packaging
capability with separate commits and shared acceptance gates.

Future planning should batch related stories into coherent capability PRs. The
goal is fewer PRs, stronger review context, less manual intervention, and no
loss of SDD/TDD discipline.

## Recommended PR Order

1. PR A: Config Diagnostics And Strict Validation Hardening.
2. PR B: Local UI Persistence And Server-Mode Decision.
3. PR C: Reporting Polish For Multi-Task, Multi-Variant, Multi-Agent Runs.
4. PR D: Release Automation And Packaging Workflow Polish.
5. PR E: Optional Adapter And Telemetry Expansion, only if justified by stable
   local artifact formats or repeated command-template friction.

## Capability Epic A: Config Diagnostics And Strict Validation Hardening

### Goal

Make configuration failures actionable before users create workspaces or spend
agent time. Users should see field-specific errors, path context, and strict
validation failures that explain exactly what to fix.

### Scope

- Improve `validate-config` diagnostics for malformed config/task YAML,
  duplicate task context, missing files, missing prompt templates, unsafe
  overlay targets, and strict Git ref checks. The diagnostics contract lives in
  `docs/config-diagnostics.md`.
- Harden strict validation around config-relative paths, overlay targets,
  filename-safe task IDs, and task-level `repo_ref` checks.
- Keep validation side-effect-free: no workspaces, agents, validation commands,
  dependency installation, or network calls.
- Update `docs/configuration.md`, `docs/task-format.md`, README snippets, and
  examples when behavior changes.

### Non-Goals

- Do not implement real network isolation.
- Do not run target repository validation commands during config validation.
- Do not add remote repo cloning, issue mining, or hosted validation services.
- Do not change the runtime package boundary or restore skill-hub docs.

### Merge Acceptance Criteria

- The capability PR includes spec, tests, implementation, docs, verification.
- Invalid config and task files fail before any workspace is created.
- Errors name the relevant file, field, task ID, variant, or overlay when that
  context is available.
- Strict mode remains local and side-effect-free.
- Existing valid examples still pass `context-eval validate-config`.

### Suggested Ralph Stories

- US-A1: Specify the config diagnostics contract and error taxonomy.
- US-A2: Add tests for field-specific config/task validation failures.
- US-A3: Harden strict Git and path validation while keeping default validation
  lightweight.
- US-A4: Update configuration/task docs, README examples, and CLI error wording.

### Test Strategy

- Spec tests for the diagnostics contract.
- Pydantic and loader tests for invalid fields, duplicate task IDs, unsafe
  overlay targets, and prompt template paths.
- CLI tests for strict and non-strict validation output.
- Regression tests proving validation does not create workspaces or run
  validation commands.
- Full verification commands after each completed story and before the PR is
  marked ready.

### Why One Capability PR

The stories all change the same user workflow: getting from YAML to a trusted
preflight result. Splitting them into separate PRs would force reviewers to
rebuild the same error model repeatedly and would risk docs/tests describing a
partial validation contract.

## Capability Epic B: Local UI Persistence And Server-Mode Decision

### Goal

Decide and implement the next local UI persistence step without weakening the
static UI safety contract. Users should know whether they are exporting YAML,
using a browser file capability, or running an explicit local server mode.

### Scope

- Write a spec that chooses the persistence model: keep static export-only,
  add browser file save, or add explicit local server mode.
- If server mode is chosen, define allowed local endpoints, destination paths,
  validation before write, and no agent execution from the UI.
- Preserve static mode as offline, self-contained HTML that can inspect config
  and run artifacts without remote dependencies.
- Keep all result display based on existing local run artifacts.
- Update `docs/local-ui-config-editor.md`, README UI usage, and tests for the
  chosen persistence behavior.

### Non-Goals

- Do not add a hosted service, remote database, multi-user dashboard, or
  background run orchestration.
- Do not let the static UI run agents, validation commands, package installs,
  or network checks.
- Do not silently overwrite config files.
- Do not make UI persistence a prerequisite for artifact inspection.

### Merge Acceptance Criteria

- The capability PR includes spec, tests, implementation, docs, verification.
- The selected persistence mode is explicit in docs and UI wording.
- Save/export behavior validates generated YAML before writing or downloading.
- Static mode remains safe and does not open sockets or write local files.
- UI tests cover config editing, matrix preview, validation feedback, and
  persistence/export controls.

### Suggested Ralph Stories

- US-B1: Specify the local UI persistence decision and safety model.
- US-B2: Add tests for the chosen save/export/server-mode contract.
- US-B3: Implement persistence controls or server endpoints within the selected
  boundary.
- US-B4: Document user workflow, failure modes, and local-only constraints.

### Test Strategy

- Spec tests for static mode, save mode, and non-goals.
- Unit tests for editable model export and validation before persistence.
- CLI/UI HTML tests for visible controls and local-only text.
- Browser or Playwright checks when interactive controls change.
- Full verification commands after each completed story and before the PR is
  marked ready.

### Why One Capability PR

Persistence is a product decision plus implementation. Splitting the decision,
UI controls, server behavior, and docs across many PRs would create ambiguous
intermediate states where users cannot tell whether the UI is export-only or
safe to save.

## Capability Epic C: Reporting Polish For Multi-Task, Multi-Variant, Multi-Agent Runs

### Goal

Make reports, exports, terminal summaries, and the local UI easier to read for
larger local run matrices while preserving the artifact-only and non-benchmark
contract.

### Scope

- Improve Markdown report templates for multi-task, multi-variant, multi-agent,
  and repeated-trial runs.
- Use `docs/multi-agent-comparison.md` as the source spec for local multi-agent
  comparison language and artifact boundaries.
- Keep variant-level analysis primary for context comparison, and show
  agent-level summaries only when more than one `agent_name` exists.
- Improve low-confidence, failed, timeout, and missing-telemetry presentation.
- Keep CSV and compact JSON deterministic and script-friendly.
- Keep compact JSON metadata stable, including controlled export timestamp
  testing and local source file accounting.
- Keep all aggregation sourced only from `results.jsonl` and optional
  `run_metadata.json`.

### Non-Goals

- Do not rerun agents to fill report gaps.
- Do not infer token or tool-call data from logs.
- Do not publish an absolute coding-agent capability ranking.
- Do not add a hosted dashboard or remote sharing workflow.

### Merge Acceptance Criteria

- The capability PR includes spec, tests, implementation, docs, verification.
- Markdown, inspect, compare, export, and UI output describe local observations
  rather than benchmark claims.
- Multi-task and multi-variant report sections remain readable with synthetic
  fixture data.
- Multi-agent sections appear only when more than one `agent_name` is present.
- Exports remain deterministic and compatible with existing compact JSON/CSV
  contracts.

### Suggested Ralph Stories

- US-C1: Specify reporting polish for large local run matrices.
- US-C2: Add report template tests for multi-task, multi-variant, multi-agent,
  failed, low-confidence, and missing-telemetry cases.
- US-C3: Implement Markdown/terminal/UI presentation improvements from local
  artifacts.
- US-C4: Update README examples and workflow docs for larger run analysis.

### Test Strategy

- Spec tests for artifact-only aggregation and non-benchmark language.
- Report snapshot-style tests with synthetic JSONL fixtures.
- CLI tests for inspect/compare output and single-agent suppression.
- Export tests for deterministic CSV and compact JSON compatibility.
- UI content tests, with browser verification if layout or interaction changes.
- Full verification commands after each completed story and before the PR is
  marked ready.

### Why One Capability PR

The reporting surfaces share one aggregation contract. Reviewing them together
prevents terminal output, Markdown, exports, and UI from drifting into slightly
different interpretations of the same run artifacts.

## Capability Epic D: Release Automation And Packaging Workflow Polish

### Goal

Turn the current manual release checklist into a reproducible packaging
workflow that catches local blockers and verifies artifacts without including
maintainer capability library files in the runtime package.

### Scope

- Consolidate release-state checks, package builds, artifact inspection,
  changelog checks, and tag/publish preparation into a clear release workflow.
- Keep CI and local release commands aligned.
- Preserve packaging scope: include `context_eval/` and report templates; reject
  `.agents/`, `.codex/skills/`, `openspec/`, `scripts/`, run artifacts, and
  active `.codex/config.toml`.
- Document supported Python versions and platform gates.
- Add automation only after the manual path remains stable in tests.

### Non-Goals

- Do not publish packages automatically without an explicit release step.
- Do not make macOS release-blocking unless a later spec changes platform
  support.
- Do not include maintainer library files in the runtime package.
- Do not commit local run artifacts or active Codex config.

### Merge Acceptance Criteria

- The capability PR includes spec, tests, implementation, docs, verification.
- Release commands are documented in one checklist and mirrored by tests or CI
  where practical.
- Built wheel and sdist artifact inspection rejects forbidden paths.
- Release-state checks catch hidden local blockers before build/publish steps.
- CHANGELOG requirements are clear for future releases.

### Suggested Ralph Stories

- US-D1: Specify release automation boundaries and manual publish checkpoints.
- US-D2: Add changelog and release-state tests for release blockers.
- US-D3: Polish scripts/CI so build and artifact inspection are reproducible.
- US-D4: Update release checklist and README verification guidance.

### Test Strategy

- Script tests for release-state and artifact inspection behavior.
- Packaging tests for wheel and sdist contents.
- CI workflow checks on Windows and Linux for Python 3.11 and 3.12.
- Docs tests for release checklist command coverage.
- Full verification commands after each completed story and before the PR is
  marked ready.

### Why One Capability PR

Release work is only useful as an end-to-end gate. Splitting build checks,
metadata, artifact inspection, changelog rules, and docs into isolated PRs
increases manual coordination and can leave the release path half-automated.

## Capability Epic E: Optional Adapter And Telemetry Expansion

### Goal

Expand adapter or telemetry support only when there is evidence that the
command-template adapter or generic JSON collector is causing repeated local
workflow friction.

### Scope

- Reassess whether a thin Python entrypoint adapter solves real repeated
  command-template friction.
- Use `docs/agent-telemetry.md` as the source spec for runner-guaranteed and
  hook-provided metrics.
- Consider agent-specific telemetry collectors only for stable local artifact
  formats that can be covered with fixtures.
- Keep the no-op collector and generic JSON collector as the default supported
  collector baseline unless evidence justifies another local format.
- Preserve backwards-compatible `CaseResult` parsing and missing-telemetry
  semantics.
- Document every new collector format before implementation.
- Keep comparisons scoped to local observations from recorded run artifacts.

### Non-Goals

- Do not add hosted API calls, provider billing reconciliation, remote cost
  accounting, or brittle log scraping.
- Do not require every agent to expose token/tool telemetry.
- Do not install or manage coding agents automatically.
- Do not turn telemetry expansion into an absolute agent benchmark.

### Merge Acceptance Criteria

- The capability PR includes spec, tests, implementation, docs, verification.
- The PR starts with evidence that the expansion is justified.
- New adapters or collectors have fixture-based tests and clear failure modes.
- Missing telemetry remains null/empty rather than guessed.
- Existing command-template configs continue to work unchanged.

### Suggested Ralph Stories

- US-E1: Decide whether adapter or telemetry expansion is justified.
- US-E2: Specify any accepted local artifact format or adapter contract.
- US-E3: Add fixture tests for parsing, errors, and backwards compatibility.
- US-E4: Implement the minimal adapter or collector and update docs.

### Test Strategy

- Spec tests for collector/adapter boundaries and non-goals.
- Model tests for backwards-compatible result parsing.
- Adapter tests for command-template compatibility and any new entrypoint.
- Collector fixture tests for collected, partial, unavailable, and error states.
- Report/export tests proving new telemetry remains local-artifact based.
- Full verification commands after each completed story and before the PR is
  marked ready.

### Why One Capability PR

Adapters and telemetry collectors affect schema, runner behavior, reports, and
docs together. Shipping them as isolated micro-PRs would make it hard to verify
that a new local artifact format is documented, parsed, reported, and exported
consistently.

## Cross-Epic Quality Gates

Every completed story should run the local gates requested for this repository:

```powershell
.\.venv\Scripts\python -m ruff check .
.\.venv\Scripts\python -m pytest --basetemp C:\tmp\context-eval-pytest
.\.venv\Scripts\context-eval validate-config --config examples/basic/context-eval.yaml
powershell -ExecutionPolicy Bypass -File scripts\validate-skills.ps1 -SkipExternal
git diff --check
```

Before a capability PR is marked ready, confirm CI status and fix failing checks
before asking for review.

## Current Replanning Stories

- US-069: Audit current development cadence and define larger capability PR
  policy.
- US-070: Replan `docs/development-plan.md` into capability epics with
  acceptance criteria.
- US-071: Document the new Ralph/SDD/TDD batching policy and changelog handoff.
