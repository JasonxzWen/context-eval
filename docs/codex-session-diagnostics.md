# Codex Session Diagnostics

Codex session diagnostics is a read-only summary workflow for local Codex
Desktop session JSONL files, such as:

```powershell
C:\Users\Admin\.codex\sessions\2026\05\27\*.jsonl
```

This workflow is separate from context-eval run inspection. It does not require
or produce `results.jsonl`, and it does not compare context variants.

## User Need

Use this workflow when you want to answer operational questions about local
Codex usage:

- How many local Codex sessions and turns were recorded for a time window?
- Which sessions produced the largest token observations?
- Which tools or functions were called most often?
- Which sessions had malformed lines, failures, rollback signals, or
  non-success tool outputs?
- Did the session logs include rate-limit observations?

These are local observations only. They are not billing records, quota
reconciliation, correctness judgments, or agent rankings.

## Command

Run:

```powershell
context-eval codex-session-summary C:\Users\Admin\.codex\sessions\2026\05\27\*.jsonl
```

Script-friendly JSON output:

```powershell
context-eval codex-session-summary C:\Users\Admin\.codex\sessions\2026\05\27\*.jsonl --format json
```

The command accepts explicit `.jsonl` files and unexpanded wildcard patterns.
Matched files are read in deterministic path order.

## Summary Scope

The terminal summary should include:

- matched session files and total bytes;
- top-level row counts such as `session_meta`, `turn_context`, `event_msg`, and
  `response_item`;
- payload counts such as `token_count`, `function_call`,
  `function_call_output`, `message`, `agent_message`, `task_started`, and
  `task_complete`;
- token observation count plus latest and maximum observed token fields when
  present;
- function/tool call counts by payload type and call name;
- output status counts;
- failure, error, rollback, malformed-line, and non-success status counts;
- rate-limit observation count;
- top sessions by size and diagnostic signal count.

JSON output should contain the same information with sorted file entries,
sorted counter keys, and explicit `null` for unavailable scalar values.

## Privacy Boundary

Default output must be content-safe. It must not print:

- user prompts;
- assistant message text;
- reasoning content;
- tool arguments;
- tool output bodies;
- full raw JSONL rows.

This workflow does not include a raw-content flag. Aggregates may include local
file paths, payload type names, tool/function names, statuses, counts,
timestamps, and sizes.

## Relationship To Existing Telemetry

Existing `codex-jsonl` telemetry is case-local and comes from `codex exec
--json` captured during a context-eval run. It feeds `results.jsonl` for run
reports and comparisons.

Codex session diagnostics reads global Codex Desktop session logs. It is for
operational review of the local Codex app history. It must not import those
sessions into `results.jsonl` or make `inspect-run` accept `.codex/sessions`
directories.

## Acceptance

This workflow is acceptable when:

- explicit files and Windows-style glob patterns are accepted;
- missing inputs fail with a concise non-zero error;
- parser tests cover known row types, known payload types, unknown payload
  types, malformed lines, token observations, tool calls, output statuses,
  rate-limit observations, and error signals;
- terminal output is concise and deterministic;
- JSON output is deterministic and omits raw content fields;
- privacy regression tests prove prompts, messages, tool arguments, and tool
  output bodies do not appear in default output;
- `inspect-run`, `compare`, `export`, and existing `codex-jsonl` telemetry
  behavior remain unchanged;
- OpenSpec validation, targeted pytest, and `git diff --check` pass.

## Non-Goals

This workflow does not:

- estimate billing cost or remaining quota;
- call hosted APIs;
- run Codex commands;
- create dashboards;
- write context-eval run artifacts;
- rank agents or judge task correctness;
- support local app UI review.
