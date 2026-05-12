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
- Report, export, compare, and static UI aggregation must read local run
  artifacts. They must not rerun agents, scrape missing telemetry from logs, or
  call hosted services.
- The active roadmap now includes an explicit local app mode for visual
  configuration, preflight, run orchestration, and result review. This is a
  local loopback app, not a hosted or multi-user dashboard.
- The active roadmap does not include an LLM judge, hosted or multi-user web
  dashboard, issue miner, real network isolation, automatic agent installation,
  provider account management, or automatic commits.

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
6. PR F: Local E2E CI Smoke And Test Taxonomy, before later feature work that
   depends on stronger workflow-level regression confidence.
7. PR G: Release Candidate Install Smoke And Changelog Finalization, before
   tagging or publishing the first 0.1.0 release candidate.
8. PR H: Agent Profiles And Noninteractive Agent Matrix, before full Web UI
   work. This unblocks Codex CLI, Claude Code, and custom commands such as
   `coco -p {prompt_file}` as first-class local profiles.
9. PR I: Local App Server And Run Orchestration, after agent profiles are
   stable. This creates the explicit local server mode behind the visual app.
10. PR J: Full Web UI Workflow For Non-Technical Users, after the server API is
    stable enough to avoid duplicating runner logic in the frontend.
11. PR K: No-CLI Launcher And Packaging, after the local app workflow is stable
    and browser-verified.

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

- Capability E keeps the command-template adapter as the only adapter for this
  PR. The accepted expansion is optional telemetry from stable local artifacts,
  not a new adapter family.
- Accepted local artifact format: the generic JSON collector described in
  `docs/agent-telemetry.md`, including documented status, source, error,
  duration, token, and tool-call fields.
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

## Capability Epic F: Local E2E CI Smoke And Test Taxonomy

### Goal

Add a clearly named local-e2e smoke layer before later feature work so CI proves
that the installed CLI can complete the main local artifact workflow, not only
unit-level behavior.

### Scope

- Use `docs/local-e2e-ci.md` as the source spec for the local-e2e smoke
  workflow and test taxonomy.
- Keep the smoke local artifact-based: fixture repository, fake local agent,
  local config files, local run artifacts, and no hosted services.
- Use no real external coding agent; the smoke must use a fake local agent
  controlled by the test fixture.
- Exercise the installed CLI through `context-eval run`, `context-eval report`,
  `context-eval export`, and `context-eval ui`.
- Verify generated `results.jsonl`, `run_manifest.json`, `report.md`,
  `summary.csv`, `summary.json`, and `context-eval-ui.html`.
- Run the smoke as a separate `local-e2e` CI job using the `local_e2e` pytest
  marker; keep that marker excluded from the default pytest matrix.
- Keep existing unit, integration, skill validation, and package-build gates.

### Non-Goals

- Do not run a real external coding agent.
- Do not install agents automatically.
- Do not call network services or hosted services.
- Do not add an LLM judge.
- Do not turn the smoke into a benchmark or leaderboard.
- Do not make Playwright browser automation required in the first local-e2e PR;
  keep it as an optional follow-up for UI-heavy changes.

### Merge Acceptance Criteria

- The capability PR includes spec, tests, implementation, docs, verification.
- The PR starts from `docs/local-e2e-ci.md` and failing contract tests.
- CI exposes a clearly named local-e2e smoke path.
- The smoke validates the installed CLI against a fixture repository and fake
  local agent.
- The smoke records and inspects local artifacts only.
- Existing CI jobs remain green on Windows and Linux.

### Suggested Ralph Stories

- US-F1: Specify local-e2e CI smoke boundaries and test taxonomy.
- US-F2: Add failing tests for the installed CLI smoke workflow.
- US-F3: Implement the minimal local-e2e smoke using a fixture repository and
  fake local agent.
- US-F4: Wire the smoke into CI with a clear job or marker boundary.
- US-F5: Update README and development verification docs with the new test
  layers.

### Test Strategy

- Spec tests for `docs/local-e2e-ci.md` and this development-plan epic.
- Subprocess CLI smoke tests using a temporary fixture repository.
- Artifact assertions for results, manifest, report, export, and static UI.
- CI workflow tests proving the local-e2e smoke is named and wired.
- Default pytest excludes `local_e2e`; run
  `python -m pytest tests/test_local_e2e_smoke.py -m local_e2e` for the
  installed CLI smoke path.
- Full verification commands after each completed story and before the PR is
  marked ready.

### Why One Capability PR

This change cuts across test taxonomy, CLI workflow, generated artifacts, CI
configuration, and developer documentation. Keeping those pieces together makes
the new gate reviewable and prevents a half-wired smoke test from becoming a
silent maintenance burden.

## Capability Epic G: Release Candidate Install Smoke And Changelog Finalization

### Goal

Prove the 0.1.0 release candidate can be installed from built package artifacts
and used through the installed CLI before maintainers tag or publish anything.

### Scope

- Use `docs/release-candidate-install-smoke.md` as the source spec for the
  release candidate install smoke.
- Run release validation from a clean archive or clean checkout when live local
  artifacts such as `.context-eval/`, `dist/`, or `context_eval.egg-info/` would
  block release-state checks.
- Build local wheel and sdist artifacts, inspect their runtime package scope,
  install the built wheel into a temporary Python environment, and run one local
  fixture repository workflow with a fake local agent.
- Keep the smoke local artifact-based: built package artifacts, local fixture
  repository, local config files, generated local run artifacts, and no hosted
  service calls.
- Finalize README, release checklist, development-plan, and changelog language
  for the 0.1.0 release candidate path.
- Stop at the manual publish checkpoint after CI and local smoke pass.

### Non-Goals

- Do not create Git tags automatically.
- Do not publish or upload packages automatically.
- Do not run against a live user repository.
- Do not install or run a real external coding agent.
- Do not call hosted services from the smoke workflow.
- Do not add an LLM judge or benchmark/leaderboard language.

### Merge Acceptance Criteria

- The capability PR includes spec, tests, implementation, docs, verification.
- `prepare-release.py` builds artifacts, inspects them, runs the release
  candidate install smoke, and then prints the manual publish checkpoint.
- CI package-build runs the same consolidated preparation path.
- The smoke installs the built package artifacts and exercises the installed CLI
  against a local fixture repository and fake local agent.
- Generated smoke artifacts are local, parseable, and self-contained.
- CHANGELOG and release docs name the release candidate path without implying
  automatic tag or publish behavior.

### Suggested Ralph Stories

- US-G1: Specify release candidate/install smoke contract and manual publish
  boundary.
- US-G2: Add failing tests for release install smoke coverage in docs, scripts,
  and CI.
- US-G3: Implement a minimal local install smoke from built package artifacts.
- US-G4: Wire the smoke into package-build and prepare-release without
  auto-publish.
- US-G5: Update README, release checklist, development plan, and CHANGELOG for
  the 0.1.0 release candidate path.

### Test Strategy

- Spec tests for `docs/release-candidate-install-smoke.md` and this development
  plan epic.
- Script tests for dry-run planning, missing wheel failures, and
  prepare-release wiring.
- CI workflow tests proving package-build uses the consolidated release
  preparation entrypoint and prepares runtime dependencies for the install
  smoke without editable-installing the project first.
- Manual clean-archive verification before release: run
  `python scripts/prepare-release.py --dist-dir <empty-dist>` from the clean
  tree and confirm the manual publish checkpoint.
- Full verification commands after each completed story and before the PR is
  marked ready.

### Why One Capability PR

This is the final release-candidate gate. Splitting docs, package build,
artifact inspection, installed-CLI smoke, changelog finalization, and CI wiring
would make it too easy to tag a commit that has only partial release evidence.

## Capability Epic H: Agent Profiles And Noninteractive Agent Matrix

### Goal

Make Codex CLI, Claude Code, and custom local commands first-class
noninteractive agent profiles before building the full visual workflow.

### Scope

- Use `docs/agent-profiles.md` and the OpenSpec
  `agent-profiles-local-app` change as the source specs.
- Preserve the existing single `agent` config as a backwards-compatible
  implicit profile.
- Add a new `agents` profile map for `codex-cli`, `claude-code`, and `custom`
  profile kinds.
- Validate command template variables and provide rendered command previews
  before an agent process starts.
- Expand run planning to agent x task x variant x trial and keep row ordering
  deterministic.
- Record selected profile names in `agent_name` and keep artifacts case-local.
- Keep reporting language scoped to local observations, not an absolute coding
  agent benchmark.

### Non-Goals

- Do not install Codex CLI, Claude Code, coco, or any other coding agent.
- Do not manage provider accounts, credentials, billing, or hosted APIs.
- Do not add a local app server or frontend in this PR.
- Do not add an LLM judge, automatic commits, or leaderboard language.

### Merge Acceptance Criteria

- The capability PR includes spec, tests, implementation, docs, verification.
- Existing single-agent configs continue to work unchanged.
- Mixed `agent` and `agents` config shapes fail with a clear diagnostic.
- Custom commands such as `coco -p {prompt_file}` are supported through the
  command-template adapter.
- Multi-agent runs produce deterministic manifests, result rows, logs, patches,
  and reports.

### Suggested Ralph Stories

- US-H1: Specify the agent profile schema, compatibility rules, and non-goals.
- US-H2: Add tests for profile parsing, command templates, and invalid mixed
  config shapes.
- US-H3: Implement profile-aware planning and runner execution.
- US-H4: Update reporting, export, UI, docs, and examples for profile-aware
  artifacts.

### Test Strategy

- Spec tests for `docs/agent-profiles.md` and OpenSpec requirements.
- Model tests for `agent` compatibility, `agents` validation, and profile kind
  handling.
- Adapter tests for supported and unknown command template variables.
- Runner integration tests with fake local agents for multi-profile matrices.
- Report/export/static UI tests proving agent summaries appear only when more
  than one `agent_name` exists.
- Full verification commands after each completed story and before the PR is
  marked ready.

### Why One Capability PR

Agent profiles affect config loading, adapter validation, runner planning,
artifact naming, reporting, exports, and UI data. Reviewing those changes
together keeps the multi-agent contract coherent and gives the later Web UI a
stable backend model.

## Capability Epic I: Local App Server And Run Orchestration

### Goal

Add an explicit local app mode that can save local evaluation files, run
side-effect-free preflight checks, start local evaluations, stream progress,
and inspect artifacts without requiring direct CLI use for the main workflow.

### Scope

- Use `docs/local-app-workflow.md` and the OpenSpec
  `agent-profiles-local-app` change as the source specs.
- Add an explicit local app/server command separate from static HTML export.
- Bind the local server to loopback by default and keep data file-based.
- Expose API surfaces for config save/load, preflight, run planning, run
  lifecycle, log streaming, artifact reads, and exports.
- The API contract must name the run lifecycle explicitly, including planning,
  start, active status, stop, completion, and artifact inspection.
- Reuse existing config validation, runner, reporting, export, and artifact
  modules instead of duplicating execution logic.
- Preserve static UI mode as offline, self-contained, and unable to run agents
  or write local files.

### Non-Goals

- Do not add the final polished frontend in this PR.
- Do not add hosted services, remote databases, shared accounts, or remote run
  orchestration.
- Do not install coding agents or project dependencies automatically.
- Do not run validation commands during side-effect-free preflight.
- Do not create commits, tags, or package publishes.

### Merge Acceptance Criteria

- The capability PR includes spec, tests, implementation, docs, verification.
- Static UI and local app mode have clear separate behavior in docs and code.
- API endpoints validate local paths and reject traversal outside allowed
  evaluation or artifact roots.
- Preflight catches config, path, Git ref, overlay, prompt template, command
  variable, optional executable, and output writability problems without
  starting agents.
- Run lifecycle endpoints write the same local artifacts as CLI runs.

### Suggested Ralph Stories

- US-I1: Specify local app API boundaries and path-safety rules.
- US-I2: Add API contract tests for save/load, preflight, run plan, run
  lifecycle, log streaming, artifacts, and exports.
- US-I3: Implement the minimal local app server and loopback startup command.
- US-I4: Add local-e2e coverage with the fixture repository and fake local
  agent.
- US-I5: Update README, local UI docs, and development verification guidance.

### Test Strategy

- Spec tests for `docs/local-app-workflow.md`.
- Unit tests for path safety, config round-tripping, and run-plan generation.
- API tests for every local app endpoint and failure path.
- Local-e2e smoke using fake local agents and local artifacts only.
- Browser verification only for any UI included in this PR.
- Full verification commands after each completed story and before the PR is
  marked ready.

### Why One Capability PR

Local app mode is a new execution boundary. Config writes, preflight,
orchestration, log streaming, and artifact reads need to be reviewed as one
local safety model rather than scattered across unrelated PRs.

## Capability Epic J: Full Web UI Workflow For Non-Technical Users

### Goal

Build a complete browser workflow for non-technical users across installation
handoff, startup, repo setup, task configuration, evaluation criteria,
preflight, run control, validation review, and result exploration.

### Scope

- Use the local app API from Capability I as the only execution surface.
- Provide first-run setup for evaluation workspace and target repo selection.
- Provide visual editors for tasks, variants, overlays, agent profiles,
  validation commands, timeouts, trials, jobs, cleanup policy, and output path.
- Show matrix preview before runs and require explicit confirmation before
  local agent execution.
- Show run progress, active case identity, log tails, stop controls, timeout
  status, and failure state.
- Show results from local artifacts: matrix overview, variant summaries,
  agent summaries, risk signals, validation output, patches, touched paths, and
  exports.
- Keep static UI export available for offline sharing of completed run views.

### Non-Goals

- Do not add a hosted service, multi-user collaboration, remote sharing, or
  remote database.
- Do not add real external coding-agent CI smoke in the first full UI PR.
- Do not hide validation uncertainty or imply correctness without validation
  commands and human review.
- Do not add decorative marketing pages instead of the actual app workflow.

### Merge Acceptance Criteria

- The capability PR includes spec, tests, implementation, docs, verification.
- A non-technical user can complete the workflow visually with the fixture repo
  and fake local agent.
- Text and controls fit across desktop and narrow browser viewports.
- UI copy distinguishes local observations from benchmark claims.
- Browser verification covers setup, config editing, preflight, run start/stop,
  results, and exports.

### Suggested Ralph Stories

- US-J1: Specify UI information architecture and primary user flows.
- US-J2: Implement setup, config, tasks, variants, and agent profile editors.
- US-J3: Implement evaluation criteria, preflight, and run confirmation views.
- US-J4: Implement progress, logs, stop controls, and failure-state views.
- US-J5: Implement result review, risk signals, patch/log links, and exports.
- US-J6: Update docs and browser verification artifacts.

### Test Strategy

- UI contract tests for view routing, controls, disabled states, and copy.
- API-backed integration tests using local fixture data.
- Browser tests across desktop and narrow viewports.
- Pixel/screenshot checks for layout regressions where practical.
- Local-e2e smoke with fake local agent through the visual flow.
- Full verification commands after each completed story and before the PR is
  marked ready.

### Why One Capability PR

The user-facing Web UI is one coherent workflow. Splitting setup, config,
preflight, execution, and results into separate merge packages would create
intermediate states where non-technical users still cannot complete the job.

## Capability Epic K: No-CLI Launcher And Packaging

### Goal

Make the stable local app workflow startable without requiring users to type a
command in a terminal.
The launcher must work without requiring users to type a command after
installation.

### Scope

- Decide the launcher and packaging approach after Capabilities H-J are stable.
- Start the local app server and open the browser automatically.
- The launcher starts the local app server and opens the browser for the user.
- Show startup diagnostics and log location when launch fails.
- Document installation, startup, upgrade, logs, and recovery for
  non-technical users.
- Keep release automation stopped at the existing manual tag and publish
  boundary unless a later release spec changes that.

### Non-Goals

- Do not add auto-update infrastructure in the first launcher PR.
- Do not package external coding agents.
- Do not manage provider credentials or local agent login state.
- Do not publish packages, create tags, or push releases automatically.

### Merge Acceptance Criteria

- The capability PR includes spec, tests, implementation, docs, verification.
- A user can launch the local app without typing a command after installation.
- Startup failures are visible with actionable local diagnostics.
- Existing CLI and local app server entrypoints continue to work for technical
  users.
- Release docs make the manual publish boundary explicit.

### Suggested Ralph Stories

- US-K1: Decide launcher packaging constraints and write the spec.
- US-K2: Add startup diagnostics and log-location tests where practical.
- US-K3: Implement the launcher or packaged shortcut.
- US-K4: Update install/start/recovery docs for non-technical users.
- US-K5: Verify packaged startup against the fixture workflow.

### Test Strategy

- Spec tests for launcher boundaries and non-goals.
- Scripted smoke tests for startup success and visible startup failure where
  practical.
- Manual verification for OS-specific launcher behavior until CI coverage is
  available.
- Local app browser verification after launcher startup.
- Full verification commands after each completed story and before the PR is
  marked ready.

### Why One Capability PR

The launcher is a product packaging layer over the local app. It should land
only after the app workflow is stable, and it should be reviewed with its
install, startup, diagnostics, and release-boundary docs together.

## Cross-Epic Quality Gates

Every completed story should run the local gates requested for this repository:

```powershell
.\.venv\Scripts\python -m ruff check .
.\.venv\Scripts\python -m pytest --basetemp C:\tmp\context-eval-pytest
.\.venv\Scripts\context-eval validate-config --config examples/basic/context-eval.yaml
powershell -ExecutionPolicy Bypass -File scripts\validate-skills.ps1 -SkipExternal
.\.venv\Scripts\python -m pytest tests\test_local_e2e_smoke.py -m local_e2e -q --basetemp C:\tmp\context-eval-local-e2e-pytest
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
- US-072: Specify agent profiles and noninteractive agent matrix planning.
- US-073: Specify local app server mode and full Web UI workflow.
- US-074: Replan post-release product expansion around non-CLI usage.
