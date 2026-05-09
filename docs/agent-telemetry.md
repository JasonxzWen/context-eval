# Agent Telemetry

This spec defines how context-eval should record per-agent usage signals such
as task duration, token counts, and tool calling counts without turning the
project into a hosted agent benchmark service.

## User Contract

A user can compare local run results across coding agents, context variants,
tasks, and trials using normalized telemetry fields in `results.jsonl`.
context-eval evaluates the effect of context variants under a recorded agent
configuration; it must not claim absolute coding-agent capability.

Telemetry is best-effort. Every case still records runner-guaranteed execution
signals even when a coding agent does not expose token or tool-call metadata.
Agent-specific data is collected through optional hooks or collectors at the
adapter boundary.

## Metric Classes

Telemetry has two classes:

- runner-guaranteed metrics: values context-eval can measure outside the agent,
  such as wall-clock duration, agent exit code, timeout state, stdout/stderr log
  paths, validation status, changed files, touched paths, and cleanup state.
- hook-provided metrics: values context-eval cannot infer reliably from a black
  box command, such as `prompt_tokens`, `completion_tokens`, `total_tokens`,
  `reasoning_tokens`, `tool_call_count`, `tool_calls_by_name`, model name,
  provider name, cache token counts, and agent-internal step counts.

Runner-guaranteed metrics must remain available for every adapter. Hook-provided
metrics may be absent, partial, or unavailable depending on the coding agent.

## Hook And Collector Model

The command-template adapter remains the default. It uses a no-op collector so
existing configs continue to behave unchanged.

Future collector support should have two phases:

1. prepare a case-local telemetry path or environment values before the agent
   command starts;
2. collect and normalize telemetry after the agent command exits.

The first concrete collector is a generic JSON telemetry collector. It reads a
local file written by the agent command and normalizes known fields into the
result schema. Agent-specific collectors for Codex, Claude Code, OpenCode,
Cursor, or other tools can be added later only when their local transcript or
hook formats are stable enough to test with fixtures.

Collectors must be local-only. They must not call a hosted API, upload logs,
perform cost estimation through a remote service, or execute agent commands on
their own.

## Result Schema

`CaseResult` should preserve existing fields and add optional normalized
telemetry fields. Missing telemetry must not break old result files.

Planned fields:

- `agent_duration_seconds`: duration of the agent command itself, excluding
  workspace setup, overlay, diff, validation, and cleanup work.
- `telemetry_status`: `unavailable`, `collected`, `partial`, or `error`.
- `telemetry_source`: a short source label, such as `none`, `json-file`, or a
  future agent-specific collector name.
- `prompt_tokens`
- `completion_tokens`
- `total_tokens`
- `reasoning_tokens`
- `tool_call_count`
- `tool_calls_by_name`

Token and tool fields should be nullable or default to zero only when the
collector can distinguish a real zero from missing data. The schema should also
allow a concise telemetry error message when collection fails.

## Reporting Behavior

`inspect-run`, `compare`, Markdown reports, and the local UI should treat
`results.jsonl` as the source of truth. Reporting should aggregate telemetry
only when the fields are available and should label partial or unavailable
telemetry clearly.

Useful aggregations include:

- completion rate by variant and agent name;
- average total case duration;
- average `agent_duration_seconds`;
- average `total_tokens`;
- average `tool_call_count`;
- common tool names from `tool_calls_by_name`.

Reports must preserve the existing warning that context-eval evaluates context
variants, not absolute agent capability.

## Non-Goals

This feature does not add an LLM judge, hosted dashboard, remote database,
managed cost accounting, provider billing reconciliation, real network
isolation, issue mining, or automatic agent installation.

It also does not require every coding agent to support token or tool telemetry.
Unsupported agents should still run with `telemetry_status` set to
`unavailable`.

## Test Plan

- Spec tests assert that this document and the development plan define the
  telemetry contract and boundaries.
- Model tests cover backwards-compatible result parsing and normalized
  telemetry field defaults.
- Adapter tests cover the no-op collector and generic JSON telemetry collector.
- Runner integration tests verify that agent command duration and collected
  telemetry are written to `results.jsonl`.
- Report and CLI tests verify aggregation behavior for collected, partial, and
  unavailable telemetry.
