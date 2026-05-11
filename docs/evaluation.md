# Evaluation

context-eval collects two MVP signals: validation command results and Git diff
stats.

## Command Evaluation

Validation commands are selected in this order:

1. `task.validation.commands`
2. `config.evaluation.commands`
3. skipped if neither exists

Each command records command text, cwd, exit code, stdout, stderr, timeout flag,
and duration.

## Validation Timeouts

Validation commands may use an optional timeout. The selected timeout is resolved
in this order:

1. `task.validation.timeout_seconds`
2. `config.evaluation.timeout_seconds`
3. no timeout when neither field is set

A timed-out validation command records `timeout=true`, `exit_code=null`, captured
stdout/stderr where available, and command duration. Any timed-out validation
command makes the case `validation_status="failed"` and, when the agent itself
completed, `status="validation_failed"`.

## Diff Evaluation

After the agent exits, context-eval runs:

```text
git diff --no-ext-diff
git diff --numstat
```

It saves the patch and records changed files, insertions, deletions, and touched
paths.

## Confidence

- `high`: validation commands exist and passed.
- `medium`: validation commands exist but one or more failed.
- `low`: no validation commands were available.

## Case Statuses

Result rows use `workspace_failed` when Git workspace preparation fails before
overlays, agent execution, or validation commands can run. This status is for
repo path, ref, or worktree setup problems and is distinct from
`internal_error`, which is reserved for unexpected runner failures after setup
has begun.

## Repeated Trials

Use `context-eval run --trials N` to repeat every selected task and variant case
`N` times. This helps inspect nondeterministic agent behavior without copying
task definitions.

Each result row includes:

- `trial_index`: the 1-based trial number for that task and variant.
- `case_id`: the stable artifact identifier for the row. With one trial, it is
  `task-id__variant`. With multiple trials, it appends `__trial-N`.

Repeated trials write distinct prompt, log, patch, artifact, and workspace paths
so result rows do not overwrite each other.

## Cleanup Policies

Use `context-eval run --cleanup-policy POLICY` to choose when case workspaces
are removed after result capture. The default cleanup policy is `never`, which
keeps created workspaces for debugging. `--cleanup` remains shorthand for `--cleanup-policy always`.

Supported policies:

- `never`: keep every created workspace.
- `always`: remove every created workspace after the case finishes.
- `successful`: remove workspaces for completed cases whose validation did not
  fail, and retain failed cases for debugging.
- `failed`: remove workspaces for failed cases, and retain successful cases for
  inspection.

Each result row records `workspace_retained` and `cleanup_status` after cleanup
handling. `cleanup_status` is `skipped` when the selected policy keeps the workspace
or no workspace was created, `succeeded` when a selected workspace was removed,
and `failed` when cleanup was selected but the workspace remained or cleanup
raised an error.

## Bounded Parallelism

Use `context-eval run --jobs N` to run multiple local cases concurrently. The
option defaults to 1, which preserves the existing serial execution behavior.
`N` must be at least 1.

Parallelism is bounded by case: each task, variant, and trial combination is
still a separate case with its own prompt, log, patch, artifact, and workspace
paths. context-eval does not rerun completed local run artifacts, install
agents, call a hosted service, or change the meaning of recorded results.

`results.jsonl` writing remains single-threaded in the main runner flow. Even
when cases finish out of order, result rows are written in planned task,
variant, and trial order. This planned task, variant, and trial order lets
script consumers compare serial and parallel runs without handling
nondeterministic row order.

## Run Manifest

Every run directory includes `run_manifest.json` as a local run artifact for
reproducibility and script inspection. The manifest is written from the selected
tasks, selected variants, and configured trials for that run. It records the
planned case matrix before result aggregation and does not rerun agents or read
completed run artifacts.

The manifest includes:

- `config_hash`: the effective run config hash, using the same output-directory
  exclusion as result rows.
- `tasks`: the selected tasks in planned order, each with `task_hash`.
- `variants`: the selected variants in planned order, each with `variant_hash`.
- `trials`: the number of trials requested for each selected task and variant.
- `case_matrix`: one entry for each planned task, variant, and trial
  combination.

`case_matrix` entries preserve planned task, variant, and trial order and
include the case ID plus the effective `task_hash` and `variant_hash` used by
the matching `results.jsonl` row. The manifest is local metadata for a recorded
run; it is not an external benchmark or hosted dashboard input.

## Result Stability

Every JSONL result row includes:

- `schema_version`
- `context_eval_version`
- `config_hash`
- `task_hash`
- `variant_hash`

The hashes are deterministic summaries of the effective config, task, and
variant records. `config_hash` excludes the run output directory so moving
artifacts does not change the experiment identity. These hashes are intended for
grouping and reproducibility checks, not for cryptographic security.

Each run directory is derived from the run start timestamp and is guarded for
uniqueness. If another run has already created the timestamp directory,
context-eval appends a numeric suffix and records that selected value as the
`run_id` in `run_metadata.json` and every `results.jsonl` row.

## Normalized Telemetry Fields

Every result row includes a local-only telemetry envelope so newer reports can
compare agent usage signals without breaking older result files. Old `results.jsonl` rows
that do not contain these fields still parse as
`telemetry_status="unavailable"` with `telemetry_source="none"`.

The telemetry envelope fields are:

- `telemetry_status`: `unavailable`, `collected`, `partial`, or `error`.
- `telemetry_source`: the collector source label, such as `none` or a future
  `json-file` collector.
- `telemetry_error`: a concise local collection error when telemetry collection
  fails.
- `agent_duration_seconds`: the agent command duration, excluding runner setup,
  overlay, diff, validation, and cleanup work when the adapter can report it.
- `prompt_tokens`, `completion_tokens`, `total_tokens`, and
  `reasoning_tokens`: nullable token counts supplied by adapter telemetry.
- `tool_call_count`: nullable total tool-call count supplied by adapter
  telemetry.
- `tool_calls_by_name`: a map of tool name to non-negative local call count.

Token and tool counts remain `null` when context-eval cannot distinguish a real
zero from unavailable data. Existing command-template runs therefore record an
explicit unavailable telemetry state while preserving the older validation and
diff fields.

Each JSONL result row also records workspace cleanup state:

- `workspace_retained`: whether a case workspace still exists after the runner
  finishes cleanup handling.
- `cleanup_status`: `skipped` when cleanup was not requested or no workspace was
  created, `succeeded` when requested cleanup removed the workspace, and
  `failed` when cleanup was requested but the workspace remained or cleanup
  raised an error.

context-eval evaluates the effect of context variants, not the absolute
capability of an agent.
