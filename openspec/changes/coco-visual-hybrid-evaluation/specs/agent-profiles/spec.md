# agent-profiles Delta

## MODIFIED Requirements

### Requirement: Named local agent profiles

The system SHALL support named local agent profiles for noninteractive coding
agent commands while preserving the existing single-agent config as a backwards
compatible shape.

#### Scenario: Coco profile kind is supported

- **WHEN** a config contains an `agents` mapping with `kind: "coco"`
- **THEN** the system validates the profile as a local noninteractive command
  profile and records the selected profile key as `agent_name`

#### Scenario: Coco kind does not imply installation or credentials

- **WHEN** a Coco profile is configured
- **THEN** context-eval treats it as a command-template profile and does not
  install Coco, manage Coco credentials, call hosted APIs, or assume structured
  telemetry is available
