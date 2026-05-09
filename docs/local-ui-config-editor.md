# Local UI Config Editor

This spec defines the next local-only step for `context-eval ui`: editing an
evaluation configuration in the generated interface and exporting YAML without
introducing a hosted service.

## User Contract

A user can open a generated local UI from an existing `context-eval.yaml`,
inspect the resolved configuration, edit supported fields, preview the selected
task x variant matrix, and export updated `context-eval.yaml` plus `tasks.yaml`
content. The UI is local-only: it works from local files and generated HTML,
with no hosted service, no remote database, no server account, and no remote
storage.

The first implementation should prefer static HTML behavior. Static mode may
offer download and copy actions for generated YAML. Direct save back to the
original files is optional future work and must require an explicit local
capability, such as a local server mode or a browser-supported file picker.

## Editable Fields

The editor should cover the fields users need before a run:

- `repo.path`
- `repo.base_ref`
- `agent.name`
- `agent.command`
- `agent.timeout_minutes`
- `agent.network`
- `evaluation.commands`
- `variants`, including variant name, description, and overlays
- overlay source and target paths
- `tasks.yaml` path
- tasks, including id, title, prompt, repo_ref, category, difficulty, and
  task-level validation commands

Fields not listed above may be displayed read-only until the runtime config
model has an explicit contract for editing them.

## Validation Behavior

The UI must keep validation side-effect-free. Editing feedback may parse edited
YAML, check required fields, detect duplicate task IDs, and show the equivalent
`context-eval validate-config --config path/to/context-eval.yaml` command for a
full local preflight.

Static UI mode must not create workspaces, run an agent command, run
`evaluation.commands`, install dependencies, write to the target repo, access
the network, or perform an agent run. Static mode means no agent run. Strict Git checks remain delegated to
`validate-config --strict` unless a later local server mode explicitly supports
running them.

## Export And Save Behavior

Export produces two YAML documents:

- `context-eval.yaml` for repo, agent, task file path, variants, output, and
  config-level evaluation commands.
- `tasks.yaml` for task definitions and task-level validation commands.

The generated YAML must be accepted by `context-eval validate-config` after the
user writes both files to disk. Static mode should provide download buttons and
copy controls for each file. It must not silently overwrite local files.

If a future save mode is added, it must be explicit about the destination path,
show which files will change, validate the generated YAML before writing, and
remain local-only.

## Edge Cases

- Empty required fields should be shown as blocking validation issues.
- Duplicate task IDs should be rejected before export.
- Variant names and task IDs should be checked against filename-safe behavior
  used by run artifacts.
- Overlay targets should remain relative paths inside the target repository.
- Missing overlay sources should be reported as local file problems.
- Multiline prompts and commands must round-trip without losing indentation.
- Unknown or not-yet-editable config fields should not be dropped silently.
- Windows and POSIX-style paths should remain readable in generated YAML.

## Non-Goals

This feature does not add a hosted service, remote database, multi-user web
dashboard, issue miner, no LLM judge, real network isolation, automatic package
installation, automatic commits, direct agent execution, or background run
orchestration from static UI mode.

## Test Plan

- Unit tests for converting loaded config and tasks into an editable model.
- Round-trip tests that export `context-eval.yaml` and `tasks.yaml`, then run
  `validate_config_files` against the exported files.
- CLI tests that generated UI HTML includes editing controls, export controls,
  local-only copy, and validation feedback.
- Browser or Playwright checks for the generated static UI once interactive
  controls exist.
- Regression tests that exported YAML preserves multiline prompts, validation
  commands, variants, overlays, and task metadata.
