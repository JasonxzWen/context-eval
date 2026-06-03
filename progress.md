# Progress

## Current State

- Active task is PR A for the onboarding shell plan on
  `codex/onboarding-score-shell`.
- The branch has been fast-forwarded to latest `origin/main` after PR #61, so
  the Harness Hub minimal harness is present and in use.
- `tasks/current-task.md` now records the PR A scope, allowed paths, forbidden
  paths, acceptance criteria, and validation commands.
- `frontend/src/scoring.ts` adds `scoreRunResults(results)` for frontend result
  scoring across correctness, speed, cost, operation complexity, and change
  scope.
- `frontend/src/types.ts` now exposes the backend `trial_index` field so PR A
  comparisons use structured trial grouping instead of inferring from logs.
- `frontend/src/scoring.test.ts` covers pass/fail precedence, pass/pass
  resource comparison, the 5-point no-clear-winner threshold, missing telemetry
  confidence handling, hard/soft evaluation correctness scoring, and structured
  trial grouping.
- No broad CSS, App shell, component, or backend changes are part of PR A.

## PR A Validation

- `node scripts\harness-validate.mjs` passed.
- `cd frontend; npm run test -- src/scoring.test.ts` passed: 6 tests.
- `cd frontend; npm run validate` passed:
  - TypeScript check passed.
  - Vitest passed: 19 tests.
  - Vite build passed.
  - Playwright E2E passed: 16 tests.
- Vitest still prints existing React `act(...)` warnings in `App.test.tsx`;
  the suite passes and this warning predates PR A.

## Harness Install State

- Harness Hub minimal harness has been installed in `D:\context-eval`.
- The install created root harness state files, `scripts/harness-validate.mjs`,
  `.harness-hub/lock.json`, and the standard `skills/` tree.
- `.harness-hub/reports/` is ignored so generated install reports stay local.
- README, configuration docs, and Harness Hub provenance docs now describe the
  installed standard minimal harness boundary.
- Ruff excludes the root `skills/` capability tree, and package artifact
  inspection rejects `.harness-hub/`, `skills/`, and root harness state files.
- `decision.md` is not part of the current Harness Hub minimal template; the
  installed state files are `progress.md`, `session-handoff.md`, and
  `tasks/current-task.md`.

## Recent Validation

- `npx -y @jasonwen/harness-hub@latest init-harness "D:\context-eval" --target standard --yes --json` passed.
- `npx -y @jasonwen/harness-hub@latest validate-harness "D:\context-eval" --json` returned exit code 0, overall 100, benchmark 100.
- `npx -y @jasonwen/harness-hub@latest status "D:\context-eval" --json` reported 43 installed components, 0 modified, 0 missing, and 169 managed files.
- `npx -y @jasonwen/harness-hub@latest update "D:\context-eval" --dry-run --json` reported no updates and no blockers.
- `node scripts\harness-validate.mjs` passed.
- `tests/test_project_readiness.py` now includes coverage for the installed
  minimal harness files and ignored generated reports.
- `ruff check .` initially failed because root `skills/` was linted as project
  code; `pyproject.toml` now excludes that maintainer capability tree.
- `ruff check .` passed after excluding `skills/`.
- `python -m pytest tests/test_project_readiness.py tests/test_package_artifact_inspection.py -q --basetemp .context-eval\pytest-tmp-harness-pr` passed: 46 passed.
- `python -m pytest -q --basetemp C:\tmp\context-eval-pytest-full-harness-pr` passed: 330 passed, 2 deselected.
- `python -m build --outdir .context-eval\dist-harness-pr` passed.
- `python scripts\inspect-package-artifacts.py .context-eval\dist-harness-pr` passed.
- `context-eval validate-config --config examples/basic/context-eval.yaml` passed.
- `context-eval validate-config --config examples/agent-matrix/context-eval.yaml` passed.
- `powershell -ExecutionPolicy Bypass -File scripts\validate-skills.ps1 -SkipExternal` passed: 82 skills.
- `git diff --check` passed.

## Notes

- Keep this file focused on current and recent state. Move old details to task summaries or archives.
- The local npm package version resolved by `npx @jasonwen/harness-hub@latest`
  is `0.1.11`; the generated lock records hub component metadata as `0.1.0`.
- `harness:website-cloner` appears in `components`, but it is an explicit
  smoke scaffold outside the `standard` target and is not managed by this lock.
- Full pytest needs a basetemp outside the repository for strict Git-repo
  validation tests; an in-repo basetemp makes temporary repos inherit the
  parent `.git` directory.
