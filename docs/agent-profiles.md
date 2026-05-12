# Agent Profiles And Noninteractive Commands

This spec defines the planned first-class model for running context-eval against
Codex CLI, Claude Code, and custom local coding agents through noninteractive
commands.

The current runtime already supports one command-template agent through
`agent.command`. This plan keeps that behavior and expands it into named agent
profiles so users can run the same task, context variant, and trial matrix
against multiple local agents without copying entire config files.

## User Contract

A user can define one or more local agent profiles. Each profile names a coding
agent and provides a noninteractive command template such as:

```yaml
agents:
  codex:
    kind: "codex-cli"
    command: "codex exec -C {workspace} - < {prompt_file}"
    timeout_minutes: 60

  claude:
    kind: "claude-code"
    command: "claude -p {prompt_file}"
    timeout_minutes: 60

  coco:
    kind: "custom"
    command: "coco -p {prompt_file}"
    timeout_minutes: 60
```

context-eval prepares the workspace, prompt file, context overlays, validation
commands, and artifact directory. The selected coding agent command runs
noninteractively from the prepared workspace and may modify files. context-eval
captures stdout, stderr, patch, diff stats, validation results, and optional
telemetry. It never commits automatically.

## Compatibility

Existing configs with a single `agent` field remain valid. The old shape:

```yaml
agent:
  name: "myAgent"
  command: "myAgent -p {prompt_file}"
```

is treated as a single implicit profile. The new `agents` map is additive and
becomes the preferred form when more than one agent is configured.

Configs must not set both a top-level `agent` and `agents` unless a later
migration spec defines explicit precedence. The first implementation should keep
the failure mode clear instead of guessing which shape wins.

## Profile Model

Each profile has:

- `name`: derived from the map key and written to result rows as `agent_name`.
- `kind`: `codex-cli`, `claude-code`, or `custom`.
- `command`: the noninteractive command template.
- `timeout_minutes`: command timeout for the coding agent process.
- `network`: recorded in results as today; still not real network isolation.
- `prompt_template`: optional path resolved relative to the config file.
- `telemetry`: optional collector config, starting with `none` and `json-file`.

The `kind` field is a profile classification for validation, presets, and UI
copy. It does not install agents and does not imply a hosted provider
integration.

## Command Template Contract

The command template supports the existing variables:

- `{workspace}`
- `{prompt}`
- `{prompt_file}`
- `{task_id}`
- `{variant}`
- `{output_dir}`
- `{telemetry_file}` when the JSON telemetry collector prepares one

The template validator must reject unknown variables before any agent command
runs. The UI must show the rendered command preview for a representative case
with sensitive values avoided or clearly local.

Commands must be noninteractive. A profile that requires login prompts, editor
prompts, or manual approval is invalid for unattended evaluation until the user
changes the local agent configuration outside context-eval.

## Built-In Presets

Built-in presets help users start, but they remain editable templates:

- `codex-cli`: a Codex CLI noninteractive command template.
- `claude-code`: a Claude Code noninteractive command template.
- `custom`: a user-supplied command such as `coco -p {prompt_file}`.

The preset layer must not assume every machine has the agent installed. Preflight
checks should verify executable availability only when requested by the user or
when the local app is running an explicit preflight.

## Agent Matrix Execution

When multiple profiles are selected, the case matrix becomes:

```text
agent x task x variant x trial
```

Every result row records `agent_name`, `task_id`, `variant`, and `trial_index`.
Artifacts remain case-local, including prompt, logs, patch, workspace, and
optional telemetry files. Row ordering should remain deterministic by selected
agent, task, variant, and trial unless a later spec changes the ordering.

## Reporting Behavior

Reports, exports, terminal summaries, and UI views continue to frame results as
local observations. Agent summaries are shown only when more than one
`agent_name` exists. context-eval must not publish an absolute coding-agent ranking.

## Failure Modes

- Unknown command template variables fail during config validation or preflight.
- Missing executables fail preflight in local app mode and fail at run time in
  CLI mode if preflight was skipped.
- Nonzero agent exit codes produce `agent_failed`.
- Timeouts produce `timeout`.
- Missing telemetry remains `unavailable`; token or tool counts must not be
  guessed from logs.

## Non-Goals

This capability does not install Codex CLI, Claude Code, coco, or any other
agent. It does not manage provider accounts, hosted APIs, remote cost
accounting, or billing reconciliation. It does not add an LLM judge, automatic
commits, or absolute leaderboard language.

## Test Plan

- Spec tests for this document and OpenSpec capability files.
- Model tests for backwards-compatible `agent` parsing and new `agents` profile
  validation.
- Adapter tests for unknown variables, rendered command previews, and telemetry
  variable preparation.
- Runner tests proving the matrix expands by agent and writes deterministic
  result rows.
- Report/export/UI tests proving multi-agent summaries appear only when more
  than one `agent_name` exists.
