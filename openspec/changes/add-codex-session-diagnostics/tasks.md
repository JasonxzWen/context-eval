## 1. Fixtures And Parser Contract

- [x] 1.1 Add compact Codex Desktop session JSONL fixtures under `tests/fixtures/codex-sessions/` covering `session_meta`, `turn_context`, `event_msg`, `response_item`, `token_count`, `function_call`, `function_call_output`, `message`, malformed lines, and unknown payload types.
- [x] 1.2 Add parser model tests in `tests/test_codex_sessions.py` for per-file row counts, payload counts, malformed-line counts, timestamps, byte sizes, and deterministic ordering.
- [x] 1.3 Implement streaming JSONL parsing in `context_eval/codex_sessions.py` without retaining raw message text, tool arguments, or tool outputs.
- [x] 1.4 Add tests for token observation normalization, including latest observed values, maximum observed values, missing fields as `None`, and no billing or quota estimates.
- [x] 1.5 Add tests for function/tool call aggregation by payload type and call name, plus output status aggregation without output body text.

## 2. Diagnostics Summary Model

- [x] 2.1 Add aggregate summary tests for multiple files, sorted session rows, sorted counter keys, total sessions, total turns, total malformed lines, and top sessions by file size.
- [x] 2.2 Implement summary aggregation helpers in `context_eval/codex_sessions.py` that combine per-file observations into a deterministic diagnostics result.
- [x] 2.3 Add tests for error, failure, rollback, and non-success status signals, including top sessions by diagnostic signal count.
- [x] 2.4 Add tests for rate-limit observation counting without quota or cost inference.

## 3. CLI

- [x] 3.1 Add CLI tests in `tests/test_cli.py` or `tests/test_codex_sessions.py` for a new `codex-session-summary` command with explicit files, Windows-style glob patterns, missing inputs, and unreadable or malformed files.
- [x] 3.2 Wire the command in `context_eval/cli.py` with repeatable path arguments and a `--format text|json` option defaulting to text.
- [x] 3.3 Implement Windows-friendly glob expansion for unexpanded wildcard strings and preserve deterministic path ordering.
- [x] 3.4 Render a concise terminal summary covering session count, turn count, token observations, payload counters, tool-call counters, output statuses, error signals, rate-limit observations, malformed lines, and top sessions.
- [x] 3.5 Render deterministic JSON with explicit `null` for unavailable scalar metrics and no raw payload bodies.

## 4. Privacy And Boundary Tests

- [x] 4.1 Add regression tests asserting terminal output does not contain fixture prompt text, assistant message text, reasoning content, tool arguments, or tool output bodies.
- [x] 4.2 Add regression tests asserting JSON output omits raw content fields while retaining aggregate counts and sizes.
- [x] 4.3 Add tests proving `inspect-run` still requires `results.jsonl` and does not treat `.codex/sessions` directories as context-eval run artifacts.
- [x] 4.4 Add tests proving the existing `codex-jsonl` collector still reads case-local `codex-events.jsonl` artifacts and not global Codex Desktop session logs.

## 5. Documentation

- [x] 5.1 Update `docs/codex-session-diagnostics.md` with the final command examples, output field definitions, privacy boundary, limitations, and acceptance checklist.
- [x] 5.2 Update `README.md` and `docs/index.md` links so users can discover the diagnostics guide.
- [x] 5.3 Update `docs/agent-telemetry.md` only if implementation wording needs to clarify the difference between case-local Codex telemetry and global Codex Desktop session diagnostics.

## 6. Validation

- [x] 6.1 Run `openspec validate add-codex-session-diagnostics`.
- [x] 6.2 Run `python -m pytest tests/test_codex_sessions.py tests/test_cli.py tests/test_runner.py --basetemp C:\tmp\context-eval-pytest`.
- [x] 6.3 Run `python -m pytest --basetemp C:\tmp\context-eval-pytest` if the implementation touches shared CLI or telemetry code beyond the new module.
- [x] 6.4 Run `git diff --check`.
- [x] 6.5 Manually smoke the command against a copied local fixture and, when available, a real path pattern such as `C:\Users\Admin\.codex\sessions\2026\05\27\*.jsonl` without printing raw content.
