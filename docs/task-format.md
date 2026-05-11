# Task Format

Tasks live in a YAML file.

```yaml
tasks:
  - id: "mail-expire-attachment"
    title: "Fix expired mail attachment claim"
    repo_ref: "abc123"
    prompt: |
      Fix the bug where expired mail attachments can still be claimed.
      Keep the change minimal and follow existing module conventions.
    category: "gameplay"
    difficulty: "medium"
    validation:
      commands:
        - "python -m pytest tests/test_mail.py"
```

Required fields:

- `id`
- `prompt`

Optional fields:

- `repo_ref`
- `title`
- `category`
- `difficulty`
- `validation.commands`

Task-level validation commands override config-level `evaluation.commands`.

## Task IDs And Repo Refs

Task IDs may be any non-empty string during default validation so existing local
task files keep loading. Strict validation requires filename-safe task IDs
because task IDs are used in local run artifact names. Use letters, numbers,
`.`, `_`, or `-`, start with a letter or number, and avoid reserved platform
filenames.

`task.repo_ref` is optional. When it is omitted, the task uses
`repo.base_ref`. In strict validation, each task-level `task.repo_ref` must
resolve to a local commit in `repo.path`.

## Filtering Tasks

`context-eval run` can select a subset of tasks without editing `tasks.yaml`:

```bash
context-eval run --config context-eval.yaml --task-id task-1
context-eval run --config context-eval.yaml --category documentation
context-eval run --config context-eval.yaml --difficulty easy
```

The filters are repeatable. Repeated values within the same dimension use OR
semantics. Different dimensions are combined with AND semantics:

```bash
context-eval run \
  --config context-eval.yaml \
  --category documentation \
  --difficulty easy \
  --difficulty medium
```

This selects tasks whose `category` is `documentation` and whose `difficulty`
is either `easy` or `medium`.

Unknown `--task-id` values fail before any workspace is created. Filtering
returns a selected task set for the run and does not mutate the loaded task
file.
