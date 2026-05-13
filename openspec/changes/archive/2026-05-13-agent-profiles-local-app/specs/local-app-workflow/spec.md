## ADDED Requirements

### Requirement: Separate static UI and local app modes

The system SHALL keep static HTML UI mode separate from local app mode so each
mode has clear safety and persistence behavior.

#### Scenario: Static UI remains offline

- **WHEN** the user generates the static UI
- **THEN** the page remains self-contained, export-only, and unable to run
  agents, validation commands, server calls, or local file writes

#### Scenario: Local app mode is explicit

- **WHEN** the user starts local app mode
- **THEN** the system runs an explicit local server bound to loopback by default
  and shows that local writes and agent execution are possible only after user
  action

### Requirement: Visual configuration workflow

The local app SHALL allow users to create, open, edit, validate, and save local
evaluation configuration without manually editing YAML.

#### Scenario: New evaluation workspace is configured

- **WHEN** a user selects a target repo and creates a new evaluation workspace
- **THEN** the UI lets them configure repo settings, tasks, variants, overlays,
  agent profiles, trials, jobs, cleanup policy, and evaluation commands

#### Scenario: Save shows destination paths

- **WHEN** the user saves `context-eval.yaml` or `tasks.yaml`
- **THEN** the UI shows the destination paths and validates generated content
  before writing

#### Scenario: Unknown config fields are preserved

- **WHEN** the app opens a config containing fields that are not yet editable
- **THEN** saving editable fields does not silently drop the unknown fields

#### Scenario: Save reloads from disk

- **WHEN** the user saves `context-eval.yaml` or `tasks.yaml`
- **THEN** the app reloads those files through the server API and shows the
  parsed disk state instead of trusting only browser state

#### Scenario: Safe task YAML editing is available

- **WHEN** the first task editor does not expose every task field visually
- **THEN** the app provides a safe `tasks.yaml` editing mode that validates and
  reparses task IDs, titles, prompts, categories, difficulty, and unknown task
  fields on save

### Requirement: Chinese local app experience

The local app SHALL present the first full Web configuration workflow in
Chinese while keeping code identifiers and artifact field names stable.

#### Scenario: Visible application copy is Chinese

- **WHEN** a user opens the local app
- **THEN** headings, buttons, status text, errors, empty states, run labels,
  preflight labels, result labels, and export labels are shown in Chinese

#### Scenario: Motion is lightweight and optional

- **WHEN** the UI shows hover, focus, active, loading, progress, or log-update
  states
- **THEN** the motion is subtle, does not reduce readability, and honors
  `prefers-reduced-motion`

### Requirement: Edited path safety

The local app SHALL reject unsafe edited paths before local files are written
or local agents can run.

#### Scenario: Config and task destination paths stay inside the workspace

- **WHEN** a save request names `config_path`, `tasks_path`, or `output_dir`
  outside the local app workspace or with `..` traversal
- **THEN** the request fails before writing files

#### Scenario: Overlay paths remain bounded

- **WHEN** an edited overlay source leaves the local app workspace or an overlay
  target is absolute or contains traversal
- **THEN** the request fails before writing files

#### Scenario: Config save has no execution side effects

- **WHEN** the user saves config or task YAML
- **THEN** the server does not run agents, install dependencies, run validation
  commands, create commits, or create run workspaces

### Requirement: Preflight before agent execution

The local app SHALL provide a side-effect-free preflight step before a run can
start.

#### Scenario: Preflight validates local setup

- **WHEN** the user runs preflight
- **THEN** the system checks YAML schema, repo path, Git refs, overlay safety,
  task IDs, prompt templates, command variables, optional executable
  availability, and output directory writability

#### Scenario: Preflight avoids expensive side effects

- **WHEN** preflight runs
- **THEN** it does not execute agent commands, run validation commands, install
  dependencies, call hosted services, create commits, or create run workspaces

### Requirement: Visual run orchestration

The local app SHALL let users start, monitor, stop, and inspect local evaluation
runs from the browser.

#### Scenario: User confirms run plan

- **WHEN** the user starts a run
- **THEN** the UI shows selected agents, tasks, variants, trials, jobs, cleanup
  policy, output directory, and case count before execution begins

#### Scenario: Active run streams progress

- **WHEN** a run is active
- **THEN** the UI shows run ID, output directory, completed case count, active
  case identity, stdout/stderr tails, timeout status, and failure state

#### Scenario: Stop action is explicit

- **WHEN** the user stops a run
- **THEN** the UI explains whether active processes are terminated and how
  workspace cleanup is handled

### Requirement: Visual result review

The local app SHALL read local run artifacts and present actionable result
views for non-technical users.

#### Scenario: Results show risk signals

- **WHEN** a completed run contains failed, timeout, low-confidence, or
  telemetry-gap cases
- **THEN** the result view highlights those cases separately from raw rows

#### Scenario: Results remain local observations

- **WHEN** the UI shows variant or agent summaries
- **THEN** the UI labels them as local observations for the recorded repo,
  tasks, variants, agents, and validation commands

#### Scenario: Export uses existing artifact contracts

- **WHEN** the user exports results
- **THEN** the app produces CSV, compact JSON, Markdown, or static HTML from
  local run artifacts without rerunning agents

### Requirement: No-command-line product path

The system SHALL plan a launcher or packaged startup path so non-technical users
do not need to operate the command line after installation.

#### Scenario: Packaged launcher starts the loopback app

- **WHEN** the packaged launcher is available and the user opens it
- **THEN** it starts the loopback local app server, opens the browser to the
  local UI, and writes a local app launcher log

#### Scenario: Startup failures show diagnostics

- **WHEN** the local app cannot start
- **THEN** the launcher or diagnostics view shows a local error message and log
  location instead of silently failing

#### Scenario: Launcher stays inside local packaging boundaries

- **WHEN** the launcher starts or fails
- **THEN** it does not install external coding agents, install target
  repository dependencies, create commits, publish packages, create tags, or
  cross the manual publish checkpoint

### Requirement: Harness readiness reference

The system SHALL use the current `JasonxzWen/skill-hub` repository only as a
selective reference for explicit build/test/validate gates and readiness
analysis boundaries.

#### Scenario: Reference gates are documented without copying Skill Hub

- **WHEN** local app harness readiness is documented
- **THEN** the documentation compares context-eval's Python, frontend,
  OpenSpec, and diff-check gates against Skill Hub's explicit build, test,
  validate, release-validate, acceptance, and readiness patterns

#### Scenario: Reference scope stays local and non-mutating

- **WHEN** the harness reference is applied in this change
- **THEN** it does not install Codex, Claude Code, traecli, coco, or Skill Hub
  assets, and it does not add a hosted dashboard, remote database, leaderboard,
  or automatic target-repository commits
