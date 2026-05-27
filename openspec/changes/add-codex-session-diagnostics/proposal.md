## Why

Users sometimes need to understand how local Codex Desktop sessions behaved
after the fact: token growth, tool-call volume, failed turns, rate-limit
signals, and unusually large sessions. Today context-eval can summarize its own
run artifacts, but it cannot read Codex Desktop session JSONL files such as
`C:\Users\Admin\.codex\sessions\2026\05\27\*.jsonl`.

This change adds a narrow, read-only diagnostics slice for those local session
artifacts without treating them as context-eval run results or agent
benchmarks.

## What Changes

- Add a dedicated Codex session diagnostics command that accepts one or more
  local Codex Desktop session JSONL paths or glob patterns.
- Parse the Codex Desktop session format as a separate artifact family from
  `codex exec --json` case-local telemetry.
- Print an aggregate terminal summary covering session count, turn count,
  token-count observations, tool-call counts, failed/error signals, rate-limit
  observations, and top sessions by size or risk signal.
- Add deterministic JSON output for script-friendly review.
- Keep the default output content-safe: aggregate metadata only, no prompt,
  message body, tool arguments, or tool output text.
- Document the workflow, accepted inputs, output fields, limitations, and
  acceptance checks.

## Capabilities

### New Capabilities

- `codex-session-diagnostics`: Read-only diagnostics over local Codex Desktop
  session JSONL files, including aggregate terminal and JSON summaries.

### Modified Capabilities

- None. Existing run inspection, comparison, reporting, telemetry collection,
  and local UI requirements remain unchanged.

## Impact

- CLI: `context_eval/cli.py`
- New diagnostics module: `context_eval/codex_sessions.py`
- Tests: CLI and parser fixtures for Codex Desktop session JSONL summaries
- Docs: README/doc index links plus a dedicated diagnostics guide
- Compatibility: no changes to `results.jsonl`, `run_metadata.json`,
  `run_manifest.json`, `inspect-run`, `compare`, `export`, or existing
  `codex-jsonl` telemetry collection
