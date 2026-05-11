# Multi-Agent Comparison

This spec defines how context-eval summarizes locally observed results across
different coding agents without claiming an absolute benchmark ranking.

## User Contract

A user can compare completed local run artifacts by `agent_name`, task,
variant, and trial. The comparison is derived only from `results.jsonl` and
`run_metadata.json`; context-eval must not rerun agents, install agents, scrape
logs, call hosted services, or infer missing telemetry.

The output frames every metric as an observation for a recorded local run:
agent command, task set, context variants, validation commands, machine state,
and telemetry collector configuration all affect the result. Reports and
exports must not describe the result as an absolute coding-agent capability
ranking.

## Source Artifacts

The source of truth is the existing run directory:

- `results.jsonl` for one row per observed case.
- `run_metadata.json` for run-level labels and configuration summaries when it
  exists.

All aggregation, terminal reporting, CSV export, compact JSON export, and
static UI display must be reproducible from these files alone.

## Comparison Dimensions

The normalized comparison contract includes these dimensions and fields:

- `agent_name`
- `task_id`
- `variant`
- `trial_index`
- `status`
- `validation_status`
- `confidence`
- `duration_seconds`
- `agent_duration_seconds`
- `prompt_tokens`
- `completion_tokens`
- `total_tokens`
- `reasoning_tokens`
- `tool_call_count`
- `tool_calls_by_name`

Missing telemetry fields remain missing. CSV exports use empty fields for
missing scalar telemetry; compact JSON exports use `null`. `tool_calls_by_name`
uses an empty object only when no tool-call map was recorded.

## Export Formats

CSV export is row oriented and deterministic:

- one row per `results.jsonl` case;
- stable column order matching the documented dimensions;
- rows sorted by `agent_name`, `task_id`, `variant`, `trial_index`, and
  `case_id`;
- `tool_calls_by_name` serialized as compact JSON with sorted tool names.

Compact JSON export is deterministic and script-friendly:

- export metadata is included at the top level with
  `export_schema_version`, `exported_at`, `source_files`, `case_count`,
  `agent_count`, `variant_count`, and `task_count`;
- run metadata is included under `run`;
- case rows are sorted with the same order as CSV;
- agent summaries are sorted by `agent_name`;
- scalar missing telemetry values are `null`;
- dictionaries use sorted keys.

`export_schema_version` is a compact JSON export contract version, independent
from result row `schema_version`. `exported_at` is the UTC time when the export
file was generated, formatted as a stable ISO 8601 string. Tests that assert
the full JSON payload should inject or freeze this timestamp instead of relying
on wall-clock time, so timestamp checks remain controllable timestamps.

`source_files` lists the local artifact filenames that were present and read,
in deterministic order. It always includes `results.jsonl`; it includes
`run_metadata.json` only when that optional file exists. The exporter must not
read other files, rerun agents, infer metadata from logs, or call external
services while producing these fields.

The count fields are derived only from parsed `results.jsonl` rows:

- `case_count` is the number of result rows.
- `agent_count` is the number of distinct `agent_name` values.
- `variant_count` is the number of distinct `variant` values.
- `task_count` is the number of distinct `task_id` values.

When `run_metadata.json` is missing, compact JSON export still succeeds with an
empty `run.metadata` object and omits `run_metadata.json` from `source_files`.
When `results.jsonl` exists but contains no result rows, compact JSON export
still succeeds with zero counts, an empty `cases` list, and an empty
`agent_summaries` list.

## Reporting Behavior

`inspect-run`, `compare`, Markdown reports, and static local UI views should
show agent-level summaries when a run contains more than one `agent_name`.
Useful agent summaries include:

- case count;
- pass rate;
- average `duration_seconds`;
- average `agent_duration_seconds`;
- average `total_tokens`;
- average `tool_call_count`;
- telemetry status counts;
- common tool names from `tool_calls_by_name`.

Single-agent runs may keep the current variant-oriented display and suppress
the agent summary to avoid redundant output.

## Large Matrix Reporting Polish

Larger local runs need a run matrix overview before detailed rows. The overview
should report task count, variant count, agent count, trial count, case count,
failed count, timeout count, low-confidence count, and telemetry-gap count from
the parsed `results.jsonl` rows. These are local observations from recorded artifacts, not benchmark claims.

Markdown reports, terminal summaries, and the static UI should aggregate cells
by `task_id` and `variant` instead of selecting a single result row. In other
words, these surfaces should aggregate cells by `task_id` and `variant` for
every task/variant intersection. Each aggregate cell should make large matrices
readable by showing case count, pass rate, status counts, validation counts,
confidence counts, agent names and trial indexes. The aggregate contract is:
case count, pass rate, status counts, validation counts, confidence counts,
agent names and trial indexes. The exact formatting may vary by surface, but
the values must be derived only from local result rows.

Reporting surfaces should make risk signals easy to find. Failed, timeout,
low-confidence, and telemetry-gap cases should be listed or summarized
separately from the raw artifact links. The risk signal set covers failed,
timeout, low-confidence, and telemetry-gap cases.
In short: failed, timeout, low-confidence, and telemetry-gap cases are
first-class reporting signals.
Telemetry-gap cases include rows whose `telemetry_status` is not `collected`;
reports must not infer missing telemetry values from logs, command output, or
neighboring rows.

## Static UI Behavior

The generated local UI may display agent summary cards or tables from run
artifacts. It must remain a static, self-contained HTML file. It must not issue
external network requests, open sockets, call a hosted dashboard, write run
artifacts, or run agents.

## Local Workflow Examples

A common workflow is to run the same task set with separate local configs, one
per coding agent. Keep the repo, variants, tasks, trials, and validation
commands aligned so the exported observations are easier to compare:

```powershell
context-eval run --config .\evals\codex\context-eval.yaml --trials 3
context-eval run --config .\evals\claude-code\context-eval.yaml --trials 3
context-eval run --config .\evals\opencode\context-eval.yaml --trials 3
```

Each config should set a distinct `agent.name` so every `results.jsonl` row has
a useful `agent_name` value:

```yaml
agent:
  name: "codex-local"
  command: "codex exec -C {workspace} - < {prompt_file}"
```

Use terminal inspection and exports against existing run directories:

```powershell
context-eval inspect-run .context-eval\runs\<run-id>
context-eval compare .context-eval\runs\<run-id>
context-eval export .context-eval\runs\<run-id> --format csv --output agent-summary.csv
context-eval export .context-eval\runs\<run-id> --format json --output agent-summary.json
context-eval ui --run-dir .context-eval\runs\<run-id> --output agent-summary.html
```

If you need one combined CSV for separate run directories, export each run and
join the files with an external script. context-eval still treats each row as a
local observation from the recorded `agent_name`, task, variant, trial, status,
duration, token, and tool-call fields.

Do not publish the output as an absolute leaderboard. The observations are only
valid for the local repository, prompts, context variants, validation commands,
agent versions, machine state, and telemetry collectors used for those runs.

## Large Run Analysis Workflow

For larger local run matrices, read the run matrix overview first, then inspect
variant metrics, task/variant cells, agent summaries, and risk signals. The
task/variant cells aggregate repeated trials and multiple agents, so a cell
represents every recorded row for that `task_id` and `variant` rather than a
single chosen case.

Risk signals include failed cases, timeout cases, low-confidence cases, and
telemetry-gap cases. agent-level summaries appear only when more than one `agent_name` exists. Use these summaries as local observations, not an absolute leaderboard.

Suggested large-run reading order:

1. `context-eval compare .context-eval\runs\<run-id>` for terminal overview and
   variant-level rates.
2. `context-eval report .context-eval\runs\<run-id>` for Markdown matrix cells,
   risk signals, artifacts, and confidence notes.
3. `context-eval export .context-eval\runs\<run-id> --format csv --output summary.csv`
   for script-friendly row analysis.
4. `context-eval ui --run-dir .context-eval\runs\<run-id> --output summary.html`
   for a static local HTML view of the same recorded artifacts.

## Non-Goals

This feature does not add an LLM judge, hosted dashboard, multi-user web
service, automatic coding-agent installation, provider billing reconciliation,
issue miner, real network isolation, automatic reruns, or absolute agent
capability ranking, and must not present an absolute agent capability ranking.

## Test Plan

- Spec tests assert this document and the development plan define the local
  artifact contract, required dimensions, deterministic exports, and non-goals.
- Export tests cover CSV and compact JSON generation from synthetic
  `results.jsonl` and `run_metadata.json` fixtures.
- Export tests cover compact JSON metadata fields, missing `run_metadata.json`,
  empty `results.jsonl`, and distinct agent, variant, and task counts.
- CLI tests cover export commands and malformed run directories.
- Inspect and compare tests cover multi-agent summaries and single-agent
  suppression.
- UI tests cover static HTML contents and local-only constraints; browser
  verification checks a generated page for visible agent telemetry summary and
  absence of external requests.
