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

The development implementation starts with:

```powershell
context-eval app
```

The packaged startup entry point is:

```powershell
context-eval-app --workspace my-eval --config context-eval.yaml
```

`context-eval-app` is the shortcut target for installers or a pinned desktop
shortcut. It starts the local server, opens the browser automatically, and
writes a local app launcher log under
`my-eval/.context-eval/logs/local-app-launcher.log`. The launcher must not hide
errors that prevent the server from starting; it should show startup diagnostics
and the log location.

The frontend build, test, and browser acceptance workflow for this app is
documented in `docs/frontend-workflow.md`. Maintainers should run
`python scripts\validate-frontend.py --install --install-browsers` when working
on the local app frontend.

## Launcher Packaging

The first launcher packaging step stays inside the existing Python package. It
adds the `context-eval-app` console script as the target that a future Windows
shortcut, Start Menu entry, or lightweight installer can call. The launcher is
not a hosted dashboard and not a separate desktop runtime.

Startup behavior:

- resolve the evaluation workspace and optional config path before starting the
  server;
- keep the default host on loopback;
- write startup diagnostics to the local app launcher log;
- start the same local app server used by `context-eval app`;
- open the browser automatically unless `--no-browser` is supplied.

Recovery:

- if startup fails, read the local app launcher log at
  `.context-eval/logs/local-app-launcher.log` inside the selected workspace;
- check that the selected config path is inside the workspace and exists;
- retry with `--no-browser` if the browser handoff is the only failing step;
- retry with `--port 0` if the default port is already in use.

Installed package smoke tests use the same launcher entry point with
`--check-startup`:

```bash
context-eval-app --workspace my-eval --config context-eval.yaml --no-browser --port 0 --check-startup
```

This startup preflight validates launcher inputs, writes the local launcher log,
and exits without opening a browser, starting the blocking server loop, running
agents, or running validation commands.

Packaging boundaries:

- the launcher does not install external coding agents;
- the launcher does not install target repository dependencies;
- the launcher does not create commits, tags, releases, or published packages;
- release automation stays stopped at the existing manual tag and publish boundary.

The first no-manual-CLI Windows package is a portable zip built from the
release wheel and frontend build output:

```powershell
python scripts/build-windows-portable.py --dist-dir C:\tmp\context-eval-dist --frontend-dist frontend\dist --output-dir C:\tmp\context-eval-dist
```

The archive is named `context-eval-windows-x64-<version>.zip` and contains
`Start Context Eval.cmd`, `scripts/start-context-eval.ps1`, a bundled
wheelhouse, `frontend/dist`, a package-local `workspace`, and a README. The
double-click path creates or reuses a private `.venv`, installs from the
bundled wheelhouse with no package index, starts `context-eval-app` with
`--frontend-dist`, opens the browser, and keeps all generated files under the
portable package directory. Release builds bundle Windows dependency wheels for
Python 3.11, 3.12, and 3.13 by default so the private `.venv` install remains
offline for those supported runtimes.

On first launch, an empty portable `workspace` must not pretend that
`./fixture-repo` exists. The local app starts in a first-run setup state with
two explicit choices:

- **Try demo** creates a package-local demo repository, initializes it as a Git
  repository, writes `context-eval.yaml`, `tasks.yaml`, context overlays, a fake
  local agent, validation command, hard-evaluation checks, and JSON telemetry.
  The demo produces a two-variant matrix where baseline and experiment can be
  compared without requiring Coco or another external coding agent.
- **Open real project** creates starter evaluation files for an existing local
  Git repository path. The user still needs to review the generated agent
  command, context overlays, and task definitions before spending agent time.

## Project And Configuration Workflow

The local app must support:

- creating a new evaluation workspace from a target repo path;
- opening an existing `context-eval.yaml`;
- saving `context-eval.yaml` and `tasks.yaml` with validation before write and
  then reloading through the server API to prove the disk state changed;
- configuring `repo.path`, `repo.base_ref`, `tasks`, variants, overlays, agent
  profiles, trials, jobs, cleanup policy, and output directory;
- showing a task x variant x agent x trial matrix preview;
- preserving unknown config fields instead of silently dropping them.

All writes must show destination paths and must not silently overwrite unrelated
files.

The first full Web configuration editor is Chinese-first. Headings, buttons,
status text, errors, empty states, preflight labels, run labels, result labels,
and export labels should be visible in Chinese. Code identifiers, file names,
YAML keys, artifact names, and API fields can remain English.

The current visual case editor lets users select a task and edit the common
case-authoring fields without touching YAML: task ID, title, prompt, category,
difficulty, expected-outcome summary, acceptance points, expected files,
validation commands, command-based hard checks, soft review rubric, and visible
context variant associations. Saving this form writes `tasks.yaml`, reloads the
server-side config, and refreshes the run plan before the user starts a run.
The raw YAML view stays available as an advanced folded view for fields that do
not yet have visual controls.

The Coco-first visual authoring slice is specified in
`docs/coco-visual-hybrid-evaluation.md`. It extends this workflow with Project,
Coco Agent, Context Variants, Tasks, Expected Outcome, Hard Evaluation, Soft
Evaluation, Run Plan, Run Execution, and Results sections. The app must keep
these controls local-only: structured authoring may save `context-eval.yaml`
and `tasks.yaml`, but agent execution still requires explicit run confirmation.

Task editing may start as a safe `tasks.yaml` editor if a full structured task
form would make the PR too large. In that mode, users can edit IDs, titles,
prompts, categories, difficulty, ordering, additions, deletions, and unknown
task fields directly in YAML. The server must validate and reparse the saved
task file after the write; it must not silently drop unknown fields.

The local app may add subtle motion for hover, focus, active, loading, progress,
and log-update states. Motion must not affect readability or narrow layouts,
and CSS must honor `prefers-reduced-motion`.

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
- hard evaluation status, score, failed checks, and sidecar links when present;
- soft evaluation payload/result status and sidecar links when present;
- validation command output;
- patch links and touched paths;
- export controls for CSV, compact JSON, Markdown, and static HTML.

All results are local observations for the selected repo, tasks, context
variants, agents, and validation commands. The UI must not present them as an
absolute coding-agent leaderboard.

## API Boundary

The local server API should be private to the local app and bind to loopback by
default. The first implementation exposes JSON endpoints under `/api/` and
serves the built frontend from `frontend/dist` when it is available. The server
has one evaluation workspace root. Config writes, output directories, run
artifact roots, and artifact-relative reads must resolve inside that workspace
root and must reject path traversal such as `..`.

Edited `config_path`, `tasks_path`, `output_dir`, overlay `source`, and overlay
`target` values are part of the write-safety boundary. `config_path`,
`tasks_path`, `output_dir`, and overlay `source` must remain inside the local
app workspace. Overlay `target` must be a safe relative target path and must not
be absolute or contain traversal.

The local app API endpoints are:

- `GET /api/health`: report loopback mode, workspace root, frontend mode, and
  optional startup config path.
- `POST /api/config/load`: load `context-eval.yaml` plus its task file and
  return raw YAML, editable model data, resolved paths, and destination paths.
- `POST /api/config/save`: validate and save `context-eval.yaml` and
  `tasks.yaml` to explicit destinations inside the workspace root while
  preserving raw YAML fields that the UI does not edit.
- `POST /api/config/save-editable`: validate the browser editable model,
  regenerate and save `tasks.yaml`, preserve the existing `context-eval.yaml`
  text, reload the config, and return the refreshed editable model plus raw
  YAML. This endpoint is for the visual case editor path.
- `POST /api/preflight`: run side-effect-free validation for schema, task IDs,
  Git refs, overlay paths, prompt templates, command variables, optional agent
  executable availability, and output directory writability.
- `POST /api/run-plan`: return the selected agent x task x variant x trial
  matrix, command previews, cleanup policy, jobs, and output directory before
  any agent command can run.
- `POST /api/runs`: start a local run only when the request includes explicit
  confirmation.
- `GET /api/runs/{id}`: return run lifecycle state, run directory, progress
  counts, failure details, and result summary when available.
- `POST /api/runs/{id}/stop`: record an explicit stop request and report the
  current cleanup behavior.
- `GET /api/runs/{id}/logs`: return local console output and available stdout
  or stderr log tails for the run.
- `GET /api/results?run_dir=...`: read local `results.jsonl` and
  `run_metadata.json` and return matrix overview, risk signals, cases, and
  summaries.
- `GET /api/artifacts?run_dir=...&path=...`: read a safe relative artifact path
  under the selected run directory.
- `GET /api/exports?run_dir=...&format=csv|json|markdown|html`: produce exports
  from local run artifacts without rerunning agents.

Endpoints must avoid running shell commands except through strict config
preflight checks and the existing runner after the user confirms execution.
Preflight must not create run directories, install dependencies, run validation
commands, run agent commands, or create commits.

Config save must also be execution-free. Saving YAML must not run agent
commands, install dependencies, run validation commands, create commits, or
create run workspaces.

## Harness Readiness Reference

This phase uses `https://github.com/JasonxzWen/skill-hub` as a selective
reference and maintainer-skill source, not as runtime app code. The inspected
reference commit for this PR is
`42c3065378e1d1d2851ca0e387e915a2841b885e`.

Useful patterns to borrow:

- explicit `build`, `test`, `validate`, and release-validation gates;
- a readable acceptance matrix that distinguishes local API, frontend,
  browser, OpenSpec, lint, and diff checks;
- readiness analysis that is evidence-backed, category-based, and read-only
  instead of a single score;
- HTML work-report generation that keeps primary report content pre-rendered,
  self-contained, source-linked, and validator-checked;
- fixture repositories and fake/local agents before any real external-agent
  smoke is considered.

Out of scope for this repository phase:

- installing Skill Hub assets into target repositories or external coding
  agents;
- copying Skill Hub's repository structure into the `context_eval` runtime;
- hosted dashboards, remote databases, or agent leaderboards;
- automatic commits to a user's target repository.

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
- Chinese-copy regression tests for visible headings, controls, status text,
  errors, empty states, preflight labels, run labels, result labels, and export
  controls.
- Frontend validation through `docs/frontend-workflow.md` and
  `scripts\validate-frontend.py --install --install-browsers` before server and
  full Web UI changes depend on frontend tooling.
- Local-e2e tests using the fixture repository and fake local agent before any
  real coding-agent smoke is considered.
