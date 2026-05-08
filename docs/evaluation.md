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

context-eval evaluates the effect of context variants, not the absolute
capability of an agent.
