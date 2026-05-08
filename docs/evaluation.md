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

Each JSONL result row also records workspace cleanup state:

- `workspace_retained`: whether a case workspace still exists after the runner
  finishes cleanup handling.
- `cleanup_status`: `skipped` when cleanup was not requested or no workspace was
  created, `succeeded` when requested cleanup removed the workspace, and
  `failed` when cleanup was requested but the workspace remained or cleanup
  raised an error.

context-eval evaluates the effect of context variants, not the absolute
capability of an agent.
