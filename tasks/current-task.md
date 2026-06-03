# Current Task

## Goal

Implement PR D for the context-eval onboarding shell plan: add structured
Codex interaction turn counting from JSONL telemetry and surface it in result
models, exports, and the frontend result detail view.

## Assumptions

- PR A, PR B, and PR C are merged into `main`.
- The repository is on a fresh branch from latest `main`:
  `codex/codex-turn-count`.
- Turn counts must come from structured Codex JSONL events only.
- Missing or unrecognized telemetry should remain `null` / `未采集`, not guessed
  from stdout or stderr.

## Non-goals

- Do not change onboarding shell layout or CSS beyond the smallest display hook
  needed for the new metric.
- Do not infer turns from unstructured logs.
- Do not change scoring weights in this PR unless a type field is needed for
  future scoring.

## Worktree / Branch

- Worktree: `C:\Users\Admin\.codex\worktrees\a3f4\context-eval`
- Branch: `codex/codex-turn-count`

## Allowed paths

- `context_eval/adapters/base.py`
- `context_eval/adapters/command.py`
- `context_eval/models.py`
- `context_eval/reporting.py`
- `context_eval/export.py`
- `context_eval/runner.py`
- `context_eval/local_app.py`
- `frontend/src/types.ts`
- `frontend/src/App.tsx`
- `frontend/src/App.test.tsx`
- `frontend/e2e/app-shell.spec.ts`
- `scripts/validate-codex-first.py`
- `tests/test_adapters.py`
- `tests/test_runner.py`
- `tests/test_local_app_server.py`
- `tests/test_codex_sessions.py`
- `tests/test_export.py`
- `progress.md`
- `session-handoff.md`
- `tasks/current-task.md`

## Forbidden paths

- Broad frontend style rewrites.
- Harness install files outside task/progress/handoff records.
- Package metadata changes unless validation proves they are required.

## Acceptance criteria

- `TelemetryCollectionResult` has `interaction_turn_count: int | null`.
- `CaseResult` has `interaction_turn_count: int | null`.
- `CodexJsonlTelemetryCollector` counts interaction turns only from structured
  JSONL events.
- Runner result creation preserves the collected turn count.
- Local app results, compare payloads, and exports include the new field.
- Frontend types include the new field.
- Result detail UI shows the metric as a structured Codex hard metric and uses
  `未采集` when it is unavailable.
- Tests cover counted turns, missing telemetry staying null, runner propagation,
  and local app/API exposure.

## Validation commands

- `python -m pytest -q tests\test_adapters.py tests\test_runner.py tests\test_local_app_server.py tests\test_codex_sessions.py`
- `python scripts\validate-codex-first.py`
- `cd frontend; npm run test`
- `cd frontend; npm run validate`
- `node scripts\harness-validate.mjs`
- `git diff --check`
- `git status --short --branch`

## Parallel writes

- Default: blocked for this task.
- Use read-only parallel commands only for inspection or validation.
- Any future parallel write work must use independent branches or worktrees,
  non-overlapping paths, and a single integration review point.

## Handoff requirements

- Update `progress.md`.
- Update `session-handoff.md`.
- Run `node scripts/harness-validate.mjs`.
- Record validation evidence and the next concrete action before handoff.
