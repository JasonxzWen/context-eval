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
