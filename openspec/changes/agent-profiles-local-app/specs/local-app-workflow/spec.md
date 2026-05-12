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

#### Scenario: Launcher starts the app

- **WHEN** the packaged launcher is available and the user opens it
- **THEN** it starts the local app server and opens the browser to the local UI

#### Scenario: Startup failure is visible

- **WHEN** the local app cannot start
- **THEN** the launcher or diagnostics view shows a local error message and log
  location instead of silently failing

