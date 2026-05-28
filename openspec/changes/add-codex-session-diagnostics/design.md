## Context

context-eval currently has two different artifact families that must stay
separate:

- context-eval run artifacts under `.context-eval/runs/<run-id>`, where
  `results.jsonl` is the source of truth for `inspect-run`, `compare`,
  reports, exports, and UI review.
- Codex telemetry artifacts captured during a context-eval case, where
  `codex exec --json` stdout is stored as case-local `codex-events.jsonl` and
  normalized by the existing `codex-jsonl` collector.

Codex Desktop also writes global session JSONL files under paths such as
`C:\Users\Admin\.codex\sessions\2026\05\27\*.jsonl`. Those files are useful for
local operational review, but their event shape is different from
`codex exec --json`. They can also contain sensitive prompts, tool arguments,
and tool outputs.

## Goals / Non-Goals

**Goals:**

- Add a read-only diagnostics path for Codex Desktop session JSONL files.
- Produce deterministic aggregate summaries for local troubleshooting.
- Keep output content-safe by default and avoid printing prompt/message/tool
  payload text.
- Keep the feature independent from context-eval run comparison semantics.
- Make parser behavior fixture-backed and tolerant of unknown future fields.

**Non-Goals:**

- Do not import Codex Desktop sessions into `results.jsonl`.
- Do not change `inspect-run`, `compare`, `export`, Markdown reports, or local
  UI behavior for existing context-eval runs.
- Do not estimate provider billing cost or reconcile account quota.
- Do not upload logs, call hosted APIs, or run Codex commands.
- Do not build a leaderboard, benchmark, or absolute agent health score.
- Do not expose full prompts, messages, tool arguments, or tool output text in
  default output.

## Decisions

### Use a dedicated CLI command

Add a command such as `codex-session-summary` instead of extending
`inspect-run`. `inspect-run` requires `results.jsonl` and communicates
controlled context-eval run observations. Codex Desktop sessions are global
operational logs, not case results.

Alternative considered: allow `inspect-run` to accept a `.codex/sessions`
directory. This was rejected because it would overload the meaning of run
inspection and make downstream output harder to reason about.

### Stream JSONL files and aggregate compact counters

The parser should read files line-by-line and update counters rather than
loading every event or payload into memory. Session files can include large
`function_call_output` payloads, and users may pass an entire day of files.

The MVP summary should retain only metadata and counts:

- session file path, byte size, first and last event timestamps;
- top-level row type counts;
- payload type counts;
- `token_count` observations and latest known token fields when available;
- function/tool call counts by `payload.name`;
- function/tool output status counts;
- error and failure signal counts;
- rate-limit observation count when present;
- missing or malformed line counts.

### Treat token observations as evidence, not billing truth

Codex Desktop `token_count` payloads are local session observations. The summary
may report latest and maximum observed token values when fields are present, but
it must label them as observations and must not compute money, quota remaining,
or billing totals.

### Default output is content-safe

Terminal and JSON output must not include message text, prompts, tool arguments,
or tool outputs unless a later accepted spec adds an explicit opt-in. For MVP,
there is no raw-content flag. File paths may appear because the user supplied
local files, but payload bodies stay out of the summary.

### JSON output is deterministic

The command should support a JSON output mode for scripts. Sort session entries
by resolved path and sort counter keys by name. Missing metrics should be
`null` or empty collections, not guessed.

## Risks / Trade-offs

- Codex Desktop session schema changes -> keep parser tolerant of unknown
  fields, add fixture tests for known row and payload types, and report unknown
  counts without failing valid files.
- Sensitive local data leaks -> aggregate by default, do not print payload text,
  and document the privacy boundary clearly.
- Users confuse diagnostics with context-eval run evaluation -> use distinct
  command names, docs, and terminal wording that say "session diagnostics" and
  "local observations".
- Large daily logs are slow or memory-heavy -> stream files, avoid retaining raw
  events, and cover multi-file parsing in tests.
- Glob behavior differs between shells -> accept repeatable path arguments and
  implement Windows-friendly glob expansion for unexpanded wildcard strings.

## Migration Plan

This is an additive feature. Existing configuration files, run directories, and
reports need no migration. Rollback is removal of the new command, module,
tests, and docs.

## Open Questions

- Final command name: `codex-session-summary` is descriptive, but
  `codex-sessions` would be shorter.
- Whether a later iteration should add CSV output after JSON output proves
  useful.
- Whether local app support is worth adding after CLI usage patterns are clear.
