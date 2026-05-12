## ADDED Requirements

### Requirement: Named local agent profiles

The system SHALL support named local agent profiles for noninteractive coding
agent commands while preserving the existing single-agent config as a backwards
compatible shape.

#### Scenario: Existing single-agent config remains valid

- **WHEN** a config contains only the existing `agent` mapping
- **THEN** the system treats it as one implicit local agent profile

#### Scenario: Multiple profiles are configured

- **WHEN** a config contains an `agents` mapping with `codex-cli`,
  `claude-code`, `traecli`, or `custom` profile kinds
- **THEN** the system validates each profile independently and records the
  selected profile key as `agent_name`

#### Scenario: Mixed config shapes are rejected

- **WHEN** a config contains both top-level `agent` and `agents`
- **THEN** validation fails with a field-specific error instead of guessing
  precedence

### Requirement: Noninteractive command template contract

The system SHALL require each agent profile to provide a noninteractive command
template that is validated before agent execution.

#### Scenario: Known template variables are accepted

- **WHEN** a profile command references supported variables such as
  `{workspace}`, `{prompt_file}`, `{task_id}`, `{variant}`, `{output_dir}`, or
  prepared telemetry variables
- **THEN** the command can be rendered for each planned case

#### Scenario: Unknown template variables fail early

- **WHEN** a profile command references an unknown template variable
- **THEN** validation or preflight fails before any agent command runs

#### Scenario: Optional executable check fails before execution

- **WHEN** a user runs `validate-config --check-agents` for a profile command
  whose executable cannot be found
- **THEN** validation fails with a profile-specific `agent.command` or
  `agents.<profile>.command` diagnostic
- **AND** no agent command, validation command, workspace setup, or installer
  runs

#### Scenario: Custom agent command is supported

- **WHEN** a user configures a custom profile command such as
  `coco -p {prompt_file}`
- **THEN** the runner executes it from the prepared workspace for selected cases

#### Scenario: traecli command is supported

- **WHEN** a user configures a `traecli` profile command such as
  `traecli -p "{prompt}"`
- **THEN** the runner renders the task prompt into the command template and
  executes it from the prepared workspace for selected cases

### Requirement: Agent matrix execution

The system SHALL expand selected profiles into the local run matrix as
agent x task x variant x trial.

#### Scenario: Multiple agents are selected

- **WHEN** two selected profiles, two tasks, two variants, and three trials are
  planned
- **THEN** the run manifest records twenty-four planned cases

#### Scenario: Result rows identify the profile

- **WHEN** a planned case finishes
- **THEN** its `results.jsonl` row includes the selected profile name in
  `agent_name`

#### Scenario: Artifact paths remain case-local

- **WHEN** multiple profiles run the same task and variant
- **THEN** prompt, log, patch, workspace, and telemetry artifact paths do not
  overwrite each other

### Requirement: Local observation reporting

The system SHALL report agent profile outcomes as local observations and MUST
NOT present them as an absolute coding-agent leaderboard.

#### Scenario: Multi-agent run displays summaries

- **WHEN** a run artifact contains more than one distinct `agent_name`
- **THEN** reports, exports, and UI views may display agent-level summaries
  labeled as local observations

#### Scenario: Single-agent run suppresses redundant agent summary

- **WHEN** a run artifact contains only one distinct `agent_name`
- **THEN** agent-level summaries remain suppressed unless a later spec changes
  that behavior
