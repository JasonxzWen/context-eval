# context-eval

context-eval is a local Context A/B Testing Framework for coding agents. It
helps engineering teams evaluate whether context assets improve task outcomes in
real Git repositories under controlled local conditions.

## What context-eval is

context-eval runs a configured coding-agent command against the same repository,
task, and validation criteria while changing only the selected context variant.
It records the resulting patch, logs, validation output, timing, diff stats,
telemetry when available, and reproducibility metadata as local artifacts.

## What problem it solves

Teams increasingly invest in agent-facing context, but it is hard to know
whether a new instruction file, documentation bundle, skill, or rule set
actually helps an agent complete project work. context-eval makes that question
inspectable by keeping the repo, task, agent command, trials, and validation
commands explicit while varying the context overlay.

Validation commands and human review still define the useful confidence
boundary. context-eval does not claim fully automated correctness from patches,
diff stats, or generated prose alone.

## What it compares

- Baseline and revised `AGENTS.md` files.
- Local docs, DeepWiki exports, and other documentation bundles.
- Skills, rules, prompts, and repo-specific guidance files.
- Named local agent profiles when you want the same context matrix observed
  across multiple configured commands.

## Minimal workflow

1. Create or initialize an evaluation directory with `context-eval init`.
2. Define tasks, context variants, agent command templates, and validation
   commands in local YAML files.
3. Run `context-eval validate-config` and optionally a dry run to inspect the
   planned matrix before any agent command runs.
4. Execute a small local evaluation with fixture or real project validation
   commands.
5. Inspect `results.jsonl`, `run_manifest.json`, logs, patches, reports,
   exports, and optional static UI output before drawing conclusions.

## Demo and project documentation

- [README quickstart](#quickstart) keeps the detailed command path in this file.
- [Demo workflow](docs/demo-workflow.md) runs the bundled fixture repository and
  fake local agent without external services or provider credentials.
- [Project documentation site entry](docs/index.md) links the public
  architecture, methodology, artifact model, FAQ, and maintainer setup pages.
- [Architecture overview](docs/architecture.md) explains the runtime flow and
  static UI vs local app boundary.
- [Evaluation methodology](docs/evaluation-methodology.md) explains what the
  comparisons can and cannot support.
- [Artifact model](docs/artifact-model.md) describes the local files used for
  reproducibility, review, debugging, and exports.
- [FAQ](docs/faq.md) answers common scope, confidence, static UI, local app,
  and artifact inspection questions.

## What it is not

- Not an agent leaderboard or public benchmark ranking.
- Not a hosted dashboard, managed service, or provider account manager.
- Not an LLM judge treated as the source of truth.
- Not an automatic coding-agent installer or target-repo dependency installer.
- Not a replacement for project tests, validation commands, or code review.
- Not an automatic commit, tag, release, or publish workflow.

## Quickstart

Install in editable mode with the test dependency used by the bundled fixture
example:

```bash
python -m pip install -e ".[dev]"
```

Initialize the self-contained fixture repository:

```bash
python examples/fixture-repo/setup_fixture_repo.py
```

Create a starter evaluation directory for your own repo:

```bash
context-eval init --directory my-eval --repo-path ../my-repo --agent-command "myAgent -p {prompt_file}"
```

Validate the example config:

```bash
context-eval validate-config --config examples/basic/context-eval.yaml
```

Run strict local preflight checks when you want Git refs and artifact-safe task
IDs checked before a run:

```bash
context-eval validate-config --strict --config examples/basic/context-eval.yaml
```

Check configured agent executables before a run when you want to catch missing
local CLIs early:

```bash
context-eval validate-config --strict --check-agents --config examples/agent-matrix/context-eval.yaml
```

Validation uses field-specific diagnostics such as
`context-eval.yaml: repo.path` and
`tasks.yaml: tasks[task-1].validation.timeout_seconds`. Default validation stays
lightweight. The strict mode also checks local Git refs and filename-safe task IDs
without running agents, validation commands, or workspace setup.
`--check-agents` checks configured command executables but still does not run agent commands
and does not install coding agents, validate provider credentials, or create workspaces.

Preview the task x variant matrix without creating workspaces or run artifacts:

```bash
context-eval run --config examples/basic/context-eval.yaml --dry-run
```

Preview a named agent profile from the multi-agent example:

```bash
context-eval run --config examples/agent-matrix/context-eval.yaml --dry-run --agent trae
```

Run an evaluation:

```bash
context-eval run --config examples/basic/context-eval.yaml
```

Run bounded parallel local cases:

```bash
context-eval run --config examples/basic/context-eval.yaml --jobs 2
```

`--jobs` defaults to 1. Higher values run concurrent local cases up to that
limit while writing deterministic local run artifacts. This speeds up a local
matrix; it is not an agent leaderboard.

Choose when workspaces are retained:

```bash
context-eval run --config examples/basic/context-eval.yaml --cleanup-policy successful
```

`--cleanup-policy` accepts `never`, `always`, `successful`, and `failed`.
`never` is the default and keeps workspaces for debugging. `--cleanup` is shorthand for `--cleanup-policy always`.

Regenerate a report:

```bash
context-eval report .context-eval/runs/<run-id>
```

Inspect an existing run in the terminal:

```bash
context-eval inspect-run .context-eval/runs/<run-id>
```

Compare variant metrics for an existing run:

```bash
context-eval compare .context-eval/runs/<run-id>
```

Export deterministic CSV or compact JSON summaries from existing run artifacts:

```bash
context-eval export .context-eval/runs/<run-id> --format csv --output summary.csv
context-eval export .context-eval/runs/<run-id> --format json --output summary.json
```

Compact JSON export metadata includes:

- `export_schema_version`: the compact JSON export contract version.
- `exported_at`: the UTC timestamp for when the export file was generated.
- `source_files`: local artifact filenames read by the exporter, always
  `results.jsonl` and optionally `run_metadata.json` when that file exists.
- `case_count`, `agent_count`, `variant_count`, and `task_count`: counts
  derived only from parsed `results.jsonl` rows.

CSV and compact JSON case rows include telemetry status fields such as
`telemetry_status`, `telemetry_source`, and `telemetry_error`, plus available
duration, token, and tool-call counts. Missing telemetry remains empty in CSV
and `null` in JSON.

These fields describe the exported local observation. They do not make the
output an absolute agent benchmark.

Generate a local visual HTML interface for config and run data:

```bash
context-eval ui --config examples/basic/context-eval.yaml --run-dir .context-eval/runs/<run-id>
```

The generated UI uses static export-only persistence. It is offline,
self-contained HTML: edit supported config fields in the browser, review the
matrix and validation feedback, then copy or download both generated YAML
documents. The static page does not save back to the original files. It does
not run agents and does not run validation commands.

Start the explicit local app when you want browser-based save, preflight, run,
log, result, and export workflows:

```bash
context-eval app --workspace my-eval --config context-eval.yaml
```

After installation, the packaged local app launcher entry point is:

```bash
context-eval-app --workspace my-eval --config context-eval.yaml
```

This entry point is intended as the shortcut target for installers or desktop
shortcuts. It starts the same loopback local app server and opens the browser automatically.
It writes a local app launcher log to
`my-eval/.context-eval/logs/local-app-launcher.log`. If startup fails, rerun
with `--no-browser` or `--port 0` and inspect that log. The launcher does not
install coding agents. It does not install target-repo dependencies.
The launcher does not create tags or publish packages.

For installed package acceptance without opening a browser or serving
indefinitely, run the startup preflight:

```bash
context-eval-app --workspace my-eval --config context-eval.yaml --no-browser --port 0 --check-startup
```

The preflight validates local launcher inputs, writes the local app launcher
log, and exits without running agents, validation commands, installers, tags, or
publish steps.

### Windows portable package

For Windows users who should not create a virtual environment, run `pip`, or
type the launcher command manually, maintainers can build a portable local app
archive after the wheel and frontend are built:

```bash
python scripts/build-windows-portable.py --dist-dir C:\tmp\context-eval-dist --frontend-dist frontend\dist --output-dir C:\tmp\context-eval-dist
```

The output is `context-eval-windows-x64-<version>.zip`. A user with Python 3.11
or newer unzips it and double-clicks `Start Context Eval.cmd`; the script
creates or reuses the package-local private `.venv`, installs from the bundled
wheelhouse, starts the loopback local app with `--frontend-dist frontend\dist`,
and opens the browser. The release wheelhouse bundles Windows dependency wheels
for Python 3.11, 3.12, and 3.13 by default.

The portable package still follows the same local-only boundaries: it does not
install coding agents, does not install target repository dependencies, does
not call hosted context-eval services, does not create tags, and does not
publish packages.

The local app binds to loopback by default and confines config writes, output
directories, and artifact reads to the selected evaluation workspace. It reuses
the same local config validation, runner, reporting, and export modules as the
CLI. Preflight checks remain side-effect-free: they do not run agents, run
validation commands, install dependencies, create commits, or create run
workspaces. Runs still require explicit confirmation from the browser.

The full local app workflow is documented in `docs/local-app-workflow.md`.
The next Coco-focused local app workflow is specified in
`docs/coco-visual-hybrid-evaluation.md`; it adds visual task authoring,
expected outcomes, deterministic hard checks, optional soft evaluation payloads,
and result review while staying local and artifact-based.
Static HTML remains the safe offline mode. Frontend build, test, and browser
acceptance tooling is documented in `docs/frontend-workflow.md`; maintainers can
run it with `python scripts\validate-frontend.py --install --install-browsers`.

After placing the exported `context-eval.yaml` and `tasks.yaml` where you want
them, run:

```bash
context-eval validate-config --config path/to/context-eval.yaml
```

For larger local run matrices, start with `context-eval compare` or
`context-eval report` to read the run matrix overview before opening raw case
artifacts. In Markdown reports, terminal summaries, and the static UI,
task/variant cells aggregate repeated trials and multiple agents instead of
selecting one representative row. The large-matrix sections call out risk signals, including failed, timeout, low-confidence, and telemetry-gap cases.
agent-level summaries appear only when more than one `agent_name` exists.
Treat these as local observations, not an absolute leaderboard.

## Configuration Example

```yaml
repo:
  path: "../game-server"
  base_ref: "main"

agent:
  name: "myAgent"
  command: "myAgent -p {prompt_file}"
  timeout_minutes: 60
  network: "disabled"

tasks: "./tasks.yaml"

variants:
  baseline:
    description: "Original AGENTS.md"
    overlays:
      - source: "./contexts/baseline/AGENTS.md"
        target: "AGENTS.md"

  experiment:
    description: "Optimized AGENTS.md with DeepWiki"
    overlays:
      - source: "./contexts/experiment/AGENTS.md"
        target: "AGENTS.md"
      - source: "./contexts/experiment/docs"
        target: "docs/deepwiki"

evaluation:
  timeout_seconds: 300
  commands:
    - "python -m pytest"
```

## Task Example

```yaml
tasks:
  - id: "mail-expire-attachment"
    title: "Fix expired mail attachment claim"
    repo_ref: "abc123"
    prompt: |
      Fix the bug where expired mail attachments can still be claimed.
      Keep the change minimal and follow existing module conventions.
    category: "gameplay"
    difficulty: "medium"
    validation:
      timeout_seconds: 60
      commands:
        - "python -m pytest tests/test_mail.py"
```

`id` and `prompt` are required. If `repo_ref` is absent, context-eval uses
`repo.base_ref`.

Validation command timeouts are optional. `evaluation.timeout_seconds` sets the
config default, and `task.validation.timeout_seconds` sets a task-level
override. The task-level timeout overrides the config default. If neither field
is set, validation commands run without a timeout. A timed-out validation command
records `timeout=true`, `exit_code=null`, and makes the case fail validation.

## Agent Adapter

The MVP uses a command-template adapter:

```yaml
agent:
  name: "myAgent"
  command: "myAgent -p {prompt_file}"
```

Supported variables:

- `{workspace}`
- `{prompt}`
- `{prompt_file}`
- `{task_id}`
- `{variant}`
- `{output_dir}`
- `{telemetry_file}` when JSON file telemetry is enabled

The command runs from the isolated workspace. The agent can modify files and run
commands, but context-eval never commits automatically.

The agent profile model is documented in `docs/agent-profiles.md`. It keeps
this single-agent shape compatible while adding named `codex-cli`,
`claude-code`, `traecli`, `coco`, and custom noninteractive profiles.

## Agent Profile Matrix Example

`examples/agent-matrix/context-eval.yaml` shows the named `agents` map for
Codex CLI, Claude Code, traecli, and a Coco unattended
`coco -y --query-timeout 10m --bash-tool-timeout 5m -p "{prompt}"` command.
It targets the same local fixture repository as the basic example and is meant
to make profile-map validation and dry-run planning easy to inspect before any
real coding agent is executed.
The `-y` flag is part of the user-editable Coco command template, not a permission grant from context-eval; replace it with explicit `--allowed-tool` flags when you want narrower Coco authorization.

```bash
context-eval validate-config --config examples/agent-matrix/context-eval.yaml
context-eval run --config examples/agent-matrix/context-eval.yaml --dry-run --agent trae
```

Run it with `--agent <profile>` for only the local agent you have configured, or
edit the command templates before running the full matrix. Results remain local
observations for the selected repo, tasks, variants, profiles, and validation
commands; they are not an absolute agent leaderboard.

Customize the prompt text with a local template file:

```yaml
agent:
  name: "myAgent"
  command: "myAgent -p {prompt_file}"
  prompt_template: "./prompts/agent-task.md"
```

Prompt templates can use variables such as `{task_id}`, `{task_title}`,
`{task_prompt}`, `{variant}`, and `{repo_ref}`. The template path is resolved
relative to the config file. A missing prompt template file fails config
validation, and an unknown template variable fails before the agent command runs.

## Optional Local Agent Telemetry

Agent telemetry is optional and comes from local artifacts only. The default
collector records `telemetry_status="unavailable"` and
`telemetry_source="none"`. It does not call hosted services, install agents, or
estimate provider billing.

Enable the generic JSON file collector only when your local agent command writes
a telemetry file:

```yaml
agent:
  name: "myAgent"
  command: "myAgent -p {prompt_file} --telemetry {telemetry_file}"
  telemetry:
    collector: "json-file"
    file: "telemetry.json"
```

`{telemetry_file}` is an absolute case-local artifact path. context-eval also
sets `CONTEXT_EVAL_TELEMETRY_FILE` to that path unless
`environment_variable: null` is configured.

The JSON object may include `agent_duration_seconds`, `prompt_tokens`,
`completion_tokens`, `total_tokens`, `reasoning_tokens`, `tool_call_count`, and
`tool_calls_by_name`. Invalid or missing fields become `partial`, `error`, or
`unavailable` telemetry states instead of guessed values.

## Context Variants

Variants overlay files or directories into the workspace before the agent runs.
Each task and variant combination gets an independent Git worktree.

```yaml
variants:
  experiment:
    overlays:
      - source: "./contexts/experiment/AGENTS.md"
        target: "AGENTS.md"
      - source: "./contexts/experiment/docs"
        target: "docs/deepwiki"
```

If a target already exists, it is replaced. No backup is needed because every run
uses a fresh workspace.

## Evaluation Confidence

- `high`: validation commands exist and passed.
- `medium`: validation commands exist but one or more failed.
- `low`: no validation commands were available.

Patch and diff data alone are useful for inspection, but they do not establish
correctness.

## Output

Each run creates `.context-eval/runs/<run-id>` with:

- `results.jsonl`
- `run_manifest.json`
- `report.md`
- prompt files
- agent stdout and stderr logs
- validation logs
- Git patches
- retained workspaces by default

`run_manifest.json` records the selected tasks, selected variants, trials, and
ordered `case_matrix` for the run. It also includes `config_hash`,
`task_hash`, and `variant_hash` values so scripts can match the planned matrix
to `results.jsonl` rows and inspect reproducibility metadata from local run
artifacts. The manifest describes one recorded local run; it is not a benchmark.

Each JSONL row includes a `schema_version`, `context_eval_version`,
`config_hash`, `task_hash`, and `variant_hash` so downstream analysis can detect
schema changes and group results by the exact evaluated inputs.

Use `--cleanup-policy` to control whether case workspaces are retained in local
run artifacts.

## Development Verification

Python 3.11 or newer is required. CI currently gates Python 3.11 and Python 3.12
on pull requests. CI currently gates Ubuntu and Windows for the runtime test
matrix. A separate local-e2e CI smoke runs the installed CLI once on Ubuntu with
Python 3.12. Windows PowerShell is required for vendored skill validation.

Before opening release-oriented changes, run the local quality gates:

```bash
python -m pytest
context-eval validate-config --config examples/basic/context-eval.yaml
python scripts/check-release-state.py
python -m build --outdir C:\tmp\context-eval-dist
python scripts/inspect-package-artifacts.py C:\tmp\context-eval-dist
python scripts/install-smoke-artifacts.py --dist-dir C:\tmp\context-eval-dist
python scripts/build-windows-portable.py --dist-dir C:\tmp\context-eval-dist --frontend-dist frontend\dist --output-dir C:\tmp\context-eval-dist
git diff --check
```

Run `ruff check .` and
`powershell -ExecutionPolicy Bypass -File scripts\validate-skills.ps1 -SkipExternal`
when the dev dependencies and Windows PowerShell are available. See
`docs/release-checklist.md` for the full release packaging scope.
When touching the planned local app frontend, run
`python scripts\validate-frontend.py --install --install-browsers`; see
`docs/frontend-workflow.md` for the frontend build, test, and browser
acceptance workflow. User-visible frontend work must also pass direct
agent-operated browser acceptance before delivery; automated checks alone are
not enough.

The default pytest command covers unit and integration tests and excludes the
installed CLI smoke marked `local_e2e`. Run the local-e2e layer explicitly when
touching CLI orchestration, generated artifacts, or CI wiring:

```bash
python -m pytest tests/test_local_e2e_smoke.py -m local_e2e
```

That smoke uses only a fixture repository, a fake local agent, local config
files, and local run artifacts. It does not call hosted services, install a real
external coding agent, add an LLM judge, or require Playwright in the default PR
gate.

For release preparation, use the consolidated command:

```bash
python scripts/prepare-release.py --dist-dir C:\tmp\context-eval-dist
```

It checks CHANGELOG.md, runs the release-state check, builds and inspects release artifacts, runs the release candidate install smoke, and does not tag or publish.

The release candidate install smoke can also be run directly:

```bash
python scripts/install-smoke-artifacts.py --dist-dir C:\tmp\context-eval-dist
```

It installs the built wheel into a temporary Python environment and runs the
installed CLI against a fixture repository, fake local agent, local config files,
and local run artifacts. It also runs the installed `context-eval-app` launcher
with `--no-browser --port 0 --check-startup` so the packaged local app entry
point is verified without opening a browser or blocking in the server loop. It
does not call hosted services, run a real external coding agent, create tags, or
publish packages.

The artifact inspection command checks the built wheel and sdist against the
runtime package scope documented there.
The release-state check catches hidden local release blockers before building package artifacts.

`context_eval/` is the runtime package. `.agents/`, `.codex/skills/`,
`openspec/`, and `scripts/` are maintainer capability library files and are not runtime package modules.

## Development Capability Library

This repository includes a vendored project-local skill and workflow library
from `JasonxzWen/skill-hub` under `.agents/`, `.codex/`, `openspec/`, and
`scripts/`. It provides reusable development skills, focused agent role configs,
OpenSpec helpers, Ralph loop utilities, and skill validation scripts for
maintainers working on context-eval. The refreshed maintainer skill set includes
HTML work reports, deep code review, reproducible diagnosis, throwaway
prototyping, and plan pressure testing; these support development handoffs and
reviews but are not runtime package features.

The upstream `AGENTS.md`, `README.md`, and general-purpose skill-hub research
docs are intentionally not included. Optional Codex configuration is provided as
`.codex/config.example.toml`; copy it to `.codex/config.toml` locally only when
you want to opt in to those maintainer workflows. See
`docs/skill-hub-import.md` for provenance and import scope.

## Roadmap

- Remote repository cloning.
- User-defined prompt templates.
- More artifact summaries.
- Optional workspace cleanup policies.
- Richer validation metadata.
- CI-friendly result comparisons.

For the staged SDD+TDD roadmap, see `docs/development-plan.md`.

context-eval compares context variants under controlled conditions. It does not
measure the absolute capability of an agent.
