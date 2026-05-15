## Overview

The capability extends the existing local runner and local app rather than
introducing a new adapter or hosted scoring system. Coco is modeled as another
noninteractive command-template profile kind, with
`coco -y --query-timeout 10m --bash-tool-timeout 5m -p "prompt"` documented as
the focused unattended command shape users can edit.

Correctness stays hybrid but deterministic-first:

- hard evaluation is computed by context-eval from local artifacts;
- soft evaluation is payload-only in the first implementation;
- validation commands remain project-owned acceptance gates;
- soft scores are never required for pass/fail.

## Data Model

`TaskConfig` gains optional fields:

- `expected_outcome`: summary, expected files, forbidden paths, acceptance
  points, expected snippets, and forbidden snippets.
- `hard_evaluation`: enabled flag, validation requirement, changed-file limit,
  required/forbidden paths, snippet checks, and optional insertion/deletion
  bounds.
- `soft_evaluation`: enabled flag, `payload-only` mode, max score, and rubric.

All repository-relative path fields reject absolute paths and traversal.
Existing task YAML remains valid because every new field is optional. Task
models allow unknown fields so parser/save/reload flows can carry through
fields that the structured editor does not yet understand.

## Hard Evaluation

The runner evaluates each case after diff collection and validation. Inputs are
the `CaseResult`, the task config, the patch path, touched paths, optional
retained workspace, and validation status. Each enabled check becomes a
structured row with `passed`, `failed`, or `skipped`.

Hard evaluation writes:

```text
artifacts/<case_id>/hard_evaluation.json
```

The sidecar has schema version, case identity, `passed`, `score`, `max_score`,
checks, and summary. A compact summary is copied into `CaseResult` so existing
`results.jsonl` parsing remains backward compatible through default values.

Snippet checks prefer retained workspace files when available and fall back to
the patch text. This preserves useful checks even when workspaces are cleaned
up, while making missing-file evidence explicit.

## Soft Evaluation

The first implementation supports only:

```yaml
soft_evaluation:
  enabled: true
  mode: "payload-only"
```

The runner writes:

```text
artifacts/<case_id>/soft_evaluation_payload.json
```

The payload includes task prompt, expected outcome summary, acceptance points,
rubric, changed files, patch excerpt, validation status, hard evaluation
summary, and log/artifact paths. It does not call hosted APIs and does not
require model credentials.

Command-mode judging is intentionally deferred because it introduces a new
execution surface and result parser. The data model can add it in a later spec
without changing payload-only behavior.

## Local App And Frontend

The API continues to read and write files inside one workspace root. New local
app behavior:

- `load_config` and `save_config` accept and preserve the new task fields.
- `preflight` validates expected outcome and evaluation path safety without
  executing agents.
- `plan_run` includes Coco profile details, expected outcome summary, and
  hard/soft enabled flags per case.
- `results` includes hard evaluation summaries and soft payload/result status.
- `read_artifact` uses existing safe run-relative artifact reads for sidecars.

The React local app adds visible sections for project, Coco agent, variants,
tasks, expected outcome, hard evaluation, soft evaluation, run plan, progress,
and result review. The UI remains operational and dense: no hosted dashboard,
marketing page, or automatic agent installation.

## Reporting And Exports

Markdown reports include hard evaluation summaries, failed hard checks, soft
payload status, key metrics, and artifact links when available. CSV and compact
JSON exports add stable hard/soft fields with empty/null defaults for older
rows.

Telemetry remains artifact-derived. Coco telemetry is read only through the
existing JSON file collector; token/tool/reasoning metrics are unavailable when
structured telemetry is absent.

## Compatibility

- Existing tasks without new fields remain valid.
- Existing `CaseResult` rows parse with hard/soft defaults.
- Existing `agent` and `agents` config shapes remain valid.
- `kind: "custom"` remains supported for historical Coco examples.
- `kind: "coco"` adds UI/preflight classification only; it does not install or
  authenticate Coco.

## Risks

- Full visual editing of every nested task criterion can make the frontend
  large. The first slice exposes structured summaries and safe YAML editing,
  plus clear review panels, while backend/API contracts support the full model.
- Workspace cleanup can remove files needed for snippet checks. Patch fallback
  and explicit skipped evidence keep the result deterministic.
- Soft command mode would add shell execution outside the agent runner. It is
  deferred.
