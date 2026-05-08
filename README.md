# context-eval

context-eval is an engineering-focused Context A/B Testing Framework for
evaluating how context assets affect coding agent task outcomes in real Git
repositories.

It compares variants such as `AGENTS.md`, DeepWiki exports, skills, docs, and
rules under controlled conditions. This is an engineering tool, not a
leaderboard.

## Why context-eval

Teams increasingly invest in context assets for coding agents, but it is hard to
know whether a new instruction file or documentation bundle actually improves
task completion. context-eval runs the same repo, task, and agent command across
multiple context variants, then captures patches, logs, timing, validation
results, and diff stats.

It does not claim fully automated correctness without validation commands or
human review.

## Use Cases

- Compare a baseline `AGENTS.md` with an optimized version.
- Measure whether DeepWiki or local docs reduce failed patches.
- Test rules or skills before rolling them into a repository.
- Build repeatable regression suites for agent-facing context changes.

## Not A Fit

- Ranking different agents on public benchmarks.
- Replacing project-specific tests or code review.
- Mining issues, judging patches with an LLM, or hosting a dashboard.
- Sandboxing network access or installing target repo dependencies.

## Quickstart

Install in editable mode with the test dependency used by the bundled fixture
example:

```bash
python -m pip install -e ".[dev]"
```

Initialize the self-contained fixture repository:

```bash
python examples/fixture-repo/setup_fixture_repo.py
```

Create a starter evaluation directory for your own repo:

```bash
context-eval init --directory my-eval --repo-path ../my-repo --agent-command "myAgent -p {prompt_file}"
```

Validate the example config:

```bash
context-eval validate-config --config examples/basic/context-eval.yaml
```

Preview the task x variant matrix without creating workspaces or run artifacts:

```bash
context-eval run --config examples/basic/context-eval.yaml --dry-run
```

Run an evaluation:

```bash
context-eval run --config examples/basic/context-eval.yaml
```

Regenerate a report:

```bash
context-eval report .context-eval/runs/<run-id>
```

Inspect an existing run in the terminal:

```bash
context-eval inspect-run .context-eval/runs/<run-id>
```

## Configuration Example

```yaml
repo:
  path: "../game-server"
  base_ref: "main"

agent:
  name: "myAgent"
  command: "myAgent -p {prompt_file}"
  timeout_minutes: 60
  network: "disabled"

tasks: "./tasks.yaml"

variants:
  baseline:
    description: "Original AGENTS.md"
    overlays:
      - source: "./contexts/baseline/AGENTS.md"
        target: "AGENTS.md"

  experiment:
    description: "Optimized AGENTS.md with DeepWiki"
    overlays:
      - source: "./contexts/experiment/AGENTS.md"
        target: "AGENTS.md"
      - source: "./contexts/experiment/docs"
        target: "docs/deepwiki"

evaluation:
  commands:
    - "python -m pytest"
```

## Task Example

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

`id` and `prompt` are required. If `repo_ref` is absent, context-eval uses
`repo.base_ref`.

## Agent Adapter

The MVP uses a command-template adapter:

```yaml
agent:
  name: "myAgent"
  command: "myAgent -p {prompt_file}"
```

Supported variables:

- `{workspace}`
- `{prompt}`
- `{prompt_file}`
- `{task_id}`
- `{variant}`
- `{output_dir}`

The command runs from the isolated workspace. The agent can modify files and run
commands, but context-eval never commits automatically.

## Context Variants

Variants overlay files or directories into the workspace before the agent runs.
Each task and variant combination gets an independent Git worktree.

```yaml
variants:
  experiment:
    overlays:
      - source: "./contexts/experiment/AGENTS.md"
        target: "AGENTS.md"
      - source: "./contexts/experiment/docs"
        target: "docs/deepwiki"
```

If a target already exists, it is replaced. No backup is needed because every run
uses a fresh workspace.

## Evaluation Confidence

- `high`: validation commands exist and passed.
- `medium`: validation commands exist but one or more failed.
- `low`: no validation commands were available.

Patch and diff data alone are useful for inspection, but they do not establish
correctness.

## Output

Each run creates `.context-eval/runs/<run-id>` with:

- `results.jsonl`
- `report.md`
- prompt files
- agent stdout and stderr logs
- validation logs
- Git patches
- retained workspaces by default

Each JSONL row includes a `schema_version`, `context_eval_version`,
`config_hash`, `task_hash`, and `variant_hash` so downstream analysis can detect
schema changes and group results by the exact evaluated inputs.

Use `--cleanup` to remove workspaces after each case.

## Development Capability Library

This repository includes a vendored project-local skill and workflow library
from `JasonxzWen/skill-hub` under `.agents/`, `.codex/`, `openspec/`, and
`scripts/`. It provides reusable development skills, focused agent role configs,
OpenSpec helpers, Ralph loop utilities, and skill validation scripts for
maintainers working on context-eval.

The upstream `AGENTS.md`, `README.md`, and general-purpose skill-hub research
docs are intentionally not included. Optional Codex configuration is provided as
`.codex/config.example.toml`; copy it to `.codex/config.toml` locally only when
you want to opt in to those maintainer workflows. See
`docs/skill-hub-import.md` for provenance and import scope.

## Roadmap

- Remote repository cloning.
- User-defined prompt templates.
- More artifact summaries.
- Optional workspace cleanup policies.
- Richer validation metadata.
- CI-friendly result comparisons.

For the staged SDD+TDD roadmap, see `docs/development-plan.md`.

context-eval compares context variants under controlled conditions. It does not
measure the absolute capability of an agent.
