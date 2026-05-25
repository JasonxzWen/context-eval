# Task Format

Tasks live in a YAML file.

```yaml
tasks:
  - id: "mail-expire-attachment"
    title: "Fix expired mail attachment claim"
    case_type: "bugfix"
    repo_ref: "abc123"
    prompt: |
      Fix the bug where expired mail attachments can still be claimed.
      Keep the change minimal and follow existing module conventions.
    category: "gameplay"
    difficulty: "medium"
    validation:
      commands:
        - "python -m pytest tests/test_mail.py"
    reference_evidence:
      summary: "Real fix changed the attachment expiry check."
      fix_ref: "def456"
      files:
        - "src/mail/attachments.py"
      notes:
        - "Used for human review and default local AI arbitration."
```

Required fields:

- `id`
- `prompt`

Optional fields:

- `repo_ref`
- `case_type`
- `title`
- `category`
- `difficulty`
- `validation.commands`
- `reference_evidence`

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

## Real Project Case Metadata

`case_type` is optional planner-facing metadata. It helps the local app choose
copy, templates, and filters. It does not change runner behavior by itself.

Supported values:

- `compile_diagnosis`: diagnose a pasted compiler or build error.
- `bugfix`: fix a known bug from a pre-fix repository version.
- `incident`: diagnose a production symptom and repair the underlying bug.
- `feature`: implement a small feature from a known starting version.
- `custom`: keep a one-off task outside the built-in templates.

`reference_evidence` records the maintainer-provided answer, real fix ref, or
important files for later review. It is not appended to the coding-agent prompt
by default. It is included in local exports and in the default local AI
arbitration materials so humans and the reviewer run can compare the agent
result against known evidence.

Supported first-pass fields:

- `summary`: short true-result or real-fix summary.
- `fix_ref`: optional Git ref, commit, PR, or internal reference name.
- `files`: important repo-relative files related to the expected answer.
- `notes`: reviewer notes or constraints.

## AI Arbitration Runner

AI arbitration defaults to local runner mode. After the evaluated case
finishes, context-eval writes `soft_evaluation_payload.json`, then asks the
same local agent profile to review the payload and local artifacts:

```yaml
soft_evaluation:
  enabled: true
  mode: "runner"
  runner_agent: null
```

If `runner_agent` is empty, context-eval uses the same agent profile that ran
the evaluated case. Advanced YAML can still name a different local agent, but
the graphical workflow intentionally does not expose arbitration as a planner
setting. The runner must return machine-readable JSON with at least
`score`; optional fields include `max_score`, `verdict`, `summary`, and
`reasons`. The raw output, stdout, stderr, exit status, duration, telemetry, and
parsed JSON are saved as local soft evidence. The score is not the truth source,
does not replace validation or human feedback, and is not used as the primary
comparison ranking score.

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
