# coco-visual-hybrid-evaluation Specification

## Purpose

Define Coco-first visual authoring, expected outcome configuration,
deterministic hard checks, optional soft evaluation payload generation, and
local result review for context-eval.

## ADDED Requirements

### Requirement: Coco-first local profile support

The system SHALL accept Coco as a first-class configured local agent profile
kind for this workflow.

#### Scenario: Coco profile validates

- **WHEN** a config contains `agents.coco.kind: "coco"` and a command such as
  `coco -y --query-timeout 10m --bash-tool-timeout 5m -p "{prompt}"`
- **THEN** config loading accepts the profile and records `agent_name` as the
  selected profile key

#### Scenario: Coco executable preflight is side-effect-free

- **WHEN** `validate-config --check-agents` or local app preflight checks Coco
- **THEN** it checks only the first executable token and does not install Coco,
  run Coco, validate credentials, run validation commands, or create workspaces

### Requirement: Structured task authoring model

The system SHALL support optional expected outcome, hard evaluation, and soft
evaluation sections in task YAML while preserving old tasks.

#### Scenario: Existing task remains valid

- **WHEN** a task has only existing fields such as `id`, `prompt`, `category`,
  `difficulty`, and `validation`
- **THEN** it parses and runs unchanged

#### Scenario: Expected outcome validates safe paths

- **WHEN** a task defines expected files, forbidden paths, or snippet check paths
- **THEN** absolute paths and traversal segments are rejected before save,
  preflight, or run execution

#### Scenario: Unknown task fields are preserved by local app save/reload

- **WHEN** the local app opens and saves a task file containing unknown task
  fields
- **THEN** the saved file and reloaded raw YAML still include those fields

### Requirement: Deterministic hard evaluation artifacts

The system SHALL compute hard evaluation from local artifacts after each case.

#### Scenario: Hard checks pass

- **WHEN** validation passes, required paths changed, forbidden paths were not
  touched, changed file limits are respected, and snippet criteria match
- **THEN** `artifacts/<case_id>/hard_evaluation.json` records `passed: true`
  with passed checks and a score

#### Scenario: Hard checks fail

- **WHEN** a required path is missing, a forbidden path changed, validation is
  required but failed, or a forbidden snippet appears
- **THEN** the sidecar records failed checks and the case result exposes a
  failed hard evaluation summary without overwriting the agent status

### Requirement: Optional soft evaluation payload

The system SHALL generate soft evaluation payloads when configured without
calling hosted model APIs.

#### Scenario: Payload-only soft evaluation writes payload

- **WHEN** `soft_evaluation.enabled: true` and `mode: "payload-only"`
- **THEN** the runner writes
  `artifacts/<case_id>/soft_evaluation_payload.json` with prompt, expected
  outcome, rubric, changed files, patch excerpt, validation status, hard
  evaluation summary, and log/artifact paths

#### Scenario: Soft score is not required

- **WHEN** no soft result is present
- **THEN** reports and the local app show payload status without making soft
  scoring part of pass/fail

### Requirement: Local app visual workflow

The local app SHALL expose Coco-first authoring and hybrid scoring review from
local files and artifacts.

#### Scenario: Run plan includes hybrid evaluation

- **WHEN** the user plans a run
- **THEN** the plan shows selected Coco profile, task x variant x trial matrix,
  expected outcome summary, and hard/soft evaluation enabled flags

#### Scenario: Results include hard and soft evidence

- **WHEN** the app loads completed results
- **THEN** each case includes hard evaluation status, score, failed checks,
  soft payload/result status, metrics, changed files, and artifact links

### Requirement: Reports and exports expose stable evaluation fields

The system SHALL surface hard/soft evaluation summaries in local reports and
exports while preserving old result parsing.

#### Scenario: CSV and JSON include new fields

- **WHEN** a run has hard or soft evaluation data
- **THEN** CSV and compact JSON exports include stable hard/soft status and
  score fields

#### Scenario: Old results remain compatible

- **WHEN** an older `results.jsonl` row lacks hard or soft fields
- **THEN** exports, reports, and local app results show unavailable defaults
  instead of failing

### Requirement: Local-only boundaries

The system SHALL keep the workflow local and artifact-based.

#### Scenario: No hosted judging or dashboard is added

- **WHEN** hard or soft evaluation is configured
- **THEN** context-eval does not call hosted model APIs, require provider keys,
  create a hosted dashboard, create an agent leaderboard, install Coco, manage
  Coco credentials, or commit target repository changes
