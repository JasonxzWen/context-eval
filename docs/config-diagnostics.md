# Config Diagnostics

Configuration diagnostics make setup failures actionable before context-eval
creates workspaces or spends agent time.

## User Contract

`context-eval validate-config` must report field-specific failures with the most
specific context available. A diagnostic should identify the file and field, and
when possible the task id, variant, overlay, or Git ref involved.

Default validation is lightweight and side-effect-free. It parses YAML, validates
the config and task schema, resolves local config-relative paths, and confirms
referenced local files exist. It does not require `repo.path` to be a Git
repository.

Strict validation adds local Git and safety checks for users who want a stronger
preflight before running an evaluation.

`--check-agents` is an optional companion check for CLI users who want
side-effect-free executable availability checks for configured agent commands.
It may be combined with `--strict`.

## Error Taxonomy

Diagnostics should fit one of these categories:

- YAML parse error: malformed YAML or a YAML root that is not a mapping.
- Schema validation: missing fields, invalid field values, or invalid nested
  records from the Pydantic models.
- Missing file: paths such as `tasks`, `agent.prompt_template`, and overlay
  `source` values that cannot be found after path resolution.
- Missing executable: optional `--check-agents` failures for `agent.command` or
  `agents.<profile>.command` when the first executable token cannot be found.
- Unsafe path: path-like fields that are absolute where a safe relative value is
  required, escape with `..`, or resolve outside the allowed base.
- Duplicate task id: repeated task identifiers in `tasks.yaml`.
- Git ref: strict-mode failures for `repo.base_ref` or `task.repo_ref`.

## Diagnostic Context

Diagnostics should include:

- the config or task file path;
- a dotted field path such as `repo.path`, `agent.prompt_template`,
  `variants.baseline.overlays[0].target`, or `tasks[build-docs].repo_ref`;
- the variant name and overlay index for overlay failures;
- the task id for task-specific failures when the task id can be parsed;
- the resolved local path when a missing file or unsafe path check fails.

When a field-specific context cannot be derived, the message should still include
the source file and the original validation detail.

## Strict Validation

`context-eval validate-config --strict` remains local and side-effect-free. It
must not create a workspace, run an agent, run a validation command, install
dependencies, or make a network call.

Strict validation checks:

- `repo.path` is a Git repository.
- `repo.base_ref` resolves to a local commit.
- each task-level `task.repo_ref` resolves to a local commit.
- overlay targets remain safe relative paths.
- task ids are filename-safe enough for downstream run artifacts.

Default validation should keep the cheap checks that do not require Git state or
target repository commands.

`context-eval validate-config --check-agents` checks configured agent command
executables without running the command. It must not create a workspace, run an
agent, run validation commands, install coding agents, or contact hosted
services.

## Non-Goals

- No hosted validation service.
- No remote repository cloning or remote ref lookup.
- No issue miner.
- No LLM judge.
- No real network isolation.
- no agent run.
- no workspace creation.
- no validation command execution.

## Test Plan

- Spec tests assert this diagnostics contract exists and is linked from the
  development plan.
- Loader tests cover malformed YAML, schema validation, missing file, unsafe
  path, duplicate task id, and filename-safe task id failures.
- CLI tests cover strict and non-strict error wording.
- Regression tests prove validation stays side-effect-free: no workspace, no
  agent run, no validation command, and no network call.
