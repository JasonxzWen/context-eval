# local-app-workflow Delta

## MODIFIED Requirements

### Requirement: Visual configuration workflow

The local app SHALL allow users to create, open, edit, validate, and save local
evaluation configuration without manually editing YAML.

#### Scenario: Coco visual authoring fields are available

- **WHEN** the user opens the local app workflow for this capability
- **THEN** the UI exposes Project, Coco Agent, Context Variants, Tasks,
  Expected Outcome, Hard Evaluation, Soft Evaluation, Run Plan, Run Execution,
  and Results sections

#### Scenario: Expected outcome and evaluation config round trip

- **WHEN** the user saves tasks with `expected_outcome`, `hard_evaluation`, or
  `soft_evaluation`
- **THEN** the server validates safe paths, writes the task YAML inside the
  workspace, and reloads from disk without silently dropping unknown fields

### Requirement: Visual result review

The local app SHALL read local run artifacts and present actionable result
views for non-technical users.

#### Scenario: Hybrid scoring evidence is visible

- **WHEN** completed run artifacts include hard evaluation or soft evaluation
  sidecars
- **THEN** the result view shows hard status, hard score, failed hard checks,
  soft payload/result status, key metrics, changed files, and safe artifact
  links
