# Progress

## Current State

- Active task is PR D for the onboarding shell plan on
  `codex/codex-turn-count`.
- PR A (#62), PR B (#63), and PR C (#64) are merged into `main`; this branch
  was created from the merged PR C tip.
- `tasks/current-task.md` records PR D scope, allowed paths, forbidden paths,
  acceptance criteria, and validation commands.
- Structured Codex JSONL telemetry now carries `interaction_turn_count` through
  `TelemetryCollectionResult`, `CaseResult`, runner persistence, local app
  result payloads, reports, CSV export, and JSON export.
- Frontend result details now show the collected interaction turn metric in the
  Codex hard-metric area and render `未采集` when the structured JSONL data is
  unavailable.
- `scripts/validate-codex-first.py` now uses a short pytest basetemp on Windows
  so the default Codex-first validation gate does not fail while preparing git
  worktrees under long evidence paths.

## PR D Validation

- Focused red run failed as expected before implementation for missing turn
  count propagation.
- Focused green run passed: 5 selected PR D tests.
- Backend PR D suite passed: 82 tests in `tests/test_adapters.py`,
  `tests/test_runner.py`, `tests/test_local_app_server.py`,
  `tests/test_codex_sessions.py`, and `tests/test_export.py`.
- `python scripts\validate-codex-first.py` initially exposed the Windows long
  path issue, then passed after the short basetemp fix:
  - Python contracts: 7 passed.
  - Frontend typecheck passed.
  - Frontend build passed.
  - Codex-first Playwright smoke passed: 2 tests.
- `cd frontend; npm run test` passed: 21 tests.
- `python -m pytest -q --basetemp C:\tmp\context-eval-pytest-full-prd` passed:
  331 passed, 2 deselected.
- `cd frontend; npm run validate` passed:
  - TypeScript check passed.
  - Vitest passed: 21 tests.
  - Vite build passed.
  - Playwright E2E passed: 16 tests.
- `node scripts\harness-validate.mjs` passed.
- `git diff --check` passed.
- Vitest still prints existing React `act(...)` warnings in `App.test.tsx`;
  the suite passes and these warnings predate PR D.

## Harness Install State

- Harness Hub minimal harness has been installed in `D:\context-eval`.
- The install created root harness state files, `scripts/harness-validate.mjs`,
  `.harness-hub/lock.json`, and the standard `skills/` tree.
- `.harness-hub/reports/` is ignored so generated install reports stay local.
- README, configuration docs, and Harness Hub provenance docs describe the
  installed standard minimal harness boundary.
- Ruff excludes the root `skills/` capability tree, and package artifact
  inspection rejects `.harness-hub/`, `skills/`, and root harness state files.

## Pending Closeout

- Review final diff, commit, push, create PR D, wait for checks, merge, and
  update `main`.
