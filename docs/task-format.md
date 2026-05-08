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
