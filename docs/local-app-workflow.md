# Local App Workflow And Full Web UI

This spec defines the planned local web application mode for users who should
not need to operate context-eval through the command line.

The existing `context-eval ui` command generates a static, self-contained HTML
page. That mode remains useful for offline inspection and export-only config
editing. The new local app mode is a separate explicit mode that can save local
configuration, run preflight checks, start evaluations, stream progress, and
show results from local artifacts.

## User Contract

A non-technical user can open context-eval as a local app and complete the full
workflow visually:

1. Install or launch the app.
2. Choose a target repository and evaluation workspace.
3. Configure tasks, context variants, agent profiles, and evaluation criteria.
4. Run preflight checks before spending agent time.
5. Start, monitor, stop, or retry local evaluation runs.
6. Review validation results, patches, logs, risk signals, and reports.
7. Export CSV, compact JSON, Markdown, or static HTML summaries.

The app remains local-only. It runs on the user's machine, reads and writes only
explicit local project files and run artifacts, and does not create hosted
dashboards, shared accounts, remote databases, or automatic commits.

## Modes

context-eval should expose two UI modes:

- Static UI: current offline HTML export mode. It can inspect config and run
  artifacts and export YAML, but it cannot save files, run validation, or start
  agents.
- Local app mode: explicit local server mode launched by the user. It can save
  selected local files, run side-effect-free preflight checks, start local agent
  runs, stream logs, and inspect local results.

Mode boundaries must be visible in UI copy and docs. Static UI must stay safe
for offline sharing. Local app mode must make local writes and agent execution
explicit before they happen.

## Installation And Startup

The development implementation may start with:

```powershell
context-eval app
```

The no-command-line product target should add a launcher or packaged shortcut
that starts the local server and opens the browser automatically. The launcher
must not hide errors that prevent the server from starting; it should show a
local diagnostics page or log location.

## Project And Configuration Workflow

The local app must support:

- creating a new evaluation workspace from a target repo path;
- opening an existing `context-eval.yaml`;
- saving `context-eval.yaml` and `tasks.yaml` with validation before write;
- configuring `repo.path`, `repo.base_ref`, `tasks`, variants, overlays, agent
  profiles, trials, jobs, cleanup policy, and output directory;
- showing a task x variant x agent x trial matrix preview;
- preserving unknown config fields instead of silently dropping them.

All writes must show destination paths and must not silently overwrite unrelated
files.

## Evaluation Criteria Workflow

Users must be able to configure acceptance checks visually:

- config-level validation commands;
- task-level validation commands;
- config-level and task-level timeouts;
- confidence meaning for passed, failed, skipped, and timed-out validation;
- cleanup policy and workspace retention behavior.

The UI should treat validation commands as the user's project-specific
acceptance criteria. It must not imply that context-eval proves correctness
without validation commands or human review.

## Preflight Workflow

Preflight is separate from run execution. It should check:

- YAML schema and required fields;
- repository path and Git refs;
- overlay source and target safety;
- task IDs and duplicate IDs;
- prompt template paths;
- selected agent profile command variables;
- optional executable availability for selected profiles;
- output directory writability.

Preflight must not run agent commands, install dependencies, run validation
commands, call hosted services, or create commits.

## Run Orchestration Workflow

The local app can start a run only after the user reviews the run plan and
confirms local agent execution. While a run is active, the UI should show:

- run ID and output directory;
- planned and completed case counts;
- active agent, task, variant, and trial;
- stdout/stderr log tails;
- timeout and failure status;
- stop/cancel controls with clear cleanup behavior.

The runner should continue writing the same local artifacts used by the CLI:
`run_metadata.json`, `run_manifest.json`, `results.jsonl`, logs, prompts,
patches, workspaces, and reports.

## Results Workflow

The results view should read local run artifacts and show:

- run matrix overview;
- variant-level summaries;
- agent-level summaries only when more than one `agent_name` exists;
- failed, timeout, low-confidence, and telemetry-gap cases;
- validation command output;
- patch links and touched paths;
- export controls for CSV, compact JSON, Markdown, and static HTML.

All results are local observations for the selected repo, tasks, context
variants, agents, and validation commands. The UI must not present them as an
absolute coding-agent leaderboard.

## API Boundary

The local server API should be private to the local app and bind to loopback by
default. Endpoints should be grouped around:

- project files and config save/load;
- side-effect-free preflight;
- run planning;
- run lifecycle;
- log streaming;
- artifact and export reading.

Endpoints must validate local paths, reject traversal outside the selected
evaluation workspace where applicable, and avoid running shell commands except
through the existing runner and explicit preflight checks.

## Non-Goals

This capability does not add a hosted service, multi-user dashboard, remote
database, remote sharing, provider billing, automatic agent installation,
automatic commits, issue mining, real network isolation, or an LLM judge.

## Test Plan

- Spec tests for this document and OpenSpec capability files.
- Unit tests for project file validation, path safety, config round-tripping,
  and run-plan construction.
- API tests for save/load, preflight, run lifecycle, logs, and artifact reads.
- UI tests for first-run setup, config editing, agent profile selection,
  evaluation criteria, preflight, run start/stop, and result review.
- Browser verification for major UI changes, including desktop and narrow
  viewport checks.
- Local-e2e tests using the fixture repository and fake local agent before any
  real coding-agent smoke is considered.

