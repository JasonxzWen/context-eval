# Artifact Model

[Back to documentation index](index.md).

Every context-eval run writes local artifacts under `.context-eval/runs/<run-id>`
unless the config selects another output directory. These files are the source
of truth for review, debugging, reproducibility checks, reports, and exports.

## Core Run Files

- `results.jsonl`: one JSON row per recorded case. Rows include task, variant,
  trial, status, validation status, confidence, hashes, diff stats, paths, and
  telemetry fields when available.
- `run_metadata.json`: run-level labels and configuration summaries used by
  reports and exports when present.
- `run_manifest.json`: the planned run matrix, including selected tasks,
  selected variants, trials, ordered cases, `config_hash`, `task_hash`, and
  `variant_hash` values.
- `report.md`: Markdown report generated from local run artifacts.

## Case-Local Files

Each case can write:

- rendered prompt files;
- agent stdout logs;
- agent stderr logs;
- validation stdout and stderr logs;
- Git patches;
- diff stat metadata;
- optional telemetry files written by the configured local agent command;
- retained workspaces, depending on cleanup policy.

Retained workspaces are useful when a failed or surprising case needs manual
inspection. Cleanup policy controls whether workspaces are kept or removed
after result capture.

## Expected Outcome And Evaluation Sidecars

The Coco-first hybrid evaluation workflow adds case-local sidecars:

- `artifacts/<case_id>/hard_evaluation.json`
- `artifacts/<case_id>/soft_evaluation_payload.json`

`hard_evaluation.json` records deterministic check results, score, max score,
pass/fail status, evidence, and summary. Checks can cover validation success,
required files, forbidden files, changed-file limits, expected snippets,
forbidden snippets, diff-stat bounds, and agent completion.

`soft_evaluation_payload.json` records review input for later human or local
judge use. It is not a hosted API call and does not make soft scores mandatory
for pass/fail.

`results.jsonl` keeps compact summary fields for stable exports and UI review:

- `hard_evaluation_status`
- `hard_evaluation_score`
- `hard_evaluation_max_score`
- `hard_evaluation_passed_checks`
- `hard_evaluation_failed_checks`
- `hard_evaluation_path`
- `soft_evaluation_status`
- `soft_evaluation_payload_path`
- `soft_evaluation_result_path`

Older rows that lack these fields remain valid and render unavailable defaults.

## Exports

`context-eval export` produces deterministic CSV or compact JSON from existing
run artifacts:

- CSV is row-oriented and script-friendly.
- Compact JSON includes export metadata, run metadata when available, case
  rows, summaries, hard evaluation summaries, and soft evaluation paths.

Exports do not rerun agents, run validation commands, call hosted services, or
infer missing data from logs.

## Hash And Schema Fields

Result rows and manifests include fields that help downstream tools group and
compare local observations:

- `schema_version`: result row schema version.
- `context_eval_version`: runtime version that wrote the row.
- `config_hash`: deterministic summary of the effective config, excluding the
  output directory so moving artifacts does not change experiment identity.
- `task_hash`: deterministic summary of the selected task.
- `variant_hash`: deterministic summary of the selected context variant.

These hashes support reproducibility and grouping. They are not security
signatures and do not turn the run into a benchmark.

## Telemetry Fields

Telemetry is optional and local-artifact based. Rows may include:

- `telemetry_status`: `unavailable`, `collected`, `partial`, or `error`.
- `telemetry_source`: collector label such as `none` or `json-file`.
- `telemetry_error`: concise local collection error when collection fails.
- `agent_duration_seconds`;
- `prompt_tokens`;
- `cached_input_tokens`;
- `completion_tokens`;
- `total_tokens`;
- `reasoning_tokens`;
- `tool_call_count`;
- `tool_calls_by_name`;
- `command_call_count`;
- `model_name`;
- `provider_name`;
- `telemetry_evidence_gaps`;
- `codex_events_path`;
- `codex_final_message_path`;
- `codex_error_reason`.

Missing telemetry is explicit. CSV exports leave missing scalar telemetry empty.
Compact JSON uses `null`. context-eval does not guess token counts, tool-call
counts, command-call counts, model metadata, or billing data from logs. Codex
artifact paths must be case-local evidence files captured during the run, not
global CLI logs.

## How Artifacts Support Review

Reproducibility comes from recorded config summaries, task and variant hashes,
the manifest, prompt files, deterministic result rows, and evaluation sidecars.

Debugging comes from stdout, stderr, validation logs, patches, status fields,
timeouts, retained workspaces, hard-check evidence, and cleanup metadata.

Downstream analysis comes from CSV and compact JSON exports. Those exports stay
grounded in `results.jsonl` and optional `run_metadata.json`, so scripts can
process completed runs without rerunning local cases.
