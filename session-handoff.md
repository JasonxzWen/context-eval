# Session Handoff

## Current Status

- Current branch: `codex/onboarding-home-shell`.
- Branch was created from latest `main` after PR #62 merged.
- Active task is PR B: default onboarding home plus score summary and explicit
  reveal of the existing detailed workbench.
- PR B implementation is complete locally and validated; next action is final
  diff hygiene, commit, push, open PR, wait for checks, and merge before
  starting PR C.

## Changed Files

- `frontend/src/App.tsx`
  - Renders `OnboardingHome` by default for all states.
  - Adds explicit `我已经有项目`, `高级工作台`, and `查看完整证据` reveal paths.
  - Runs demo bootstrap from the onboarding primary action when no config is
    loaded, then starts the evaluation with the loaded demo scope.
  - Keeps the existing detailed workbench mounted only after an explicit reveal.
- `frontend/src/components/OnboardingHome.tsx`
  - New onboarding shell for empty, ready, running, completed, and failed
    states.
  - Shows the correct primary action for empty and configured workspaces.
  - Shows linear progress while a run is active.
- `frontend/src/components/RunScoreSummary.tsx`
  - New concise completed-run summary backed by `scoreRunResults`.
  - Displays scores, recommendation/no clear winner, resource metrics, changed
    files, and evidence confidence.
- `frontend/src/styles.css`
  - Adds scoped styles for the onboarding shell and score summary only.
- `frontend/src/App.test.tsx`
  - Adds unit coverage for default onboarding, demo run, score summary, and
    full-evidence reveal.
  - Updates old workbench tests to open `高级工作台` or `我已经有项目`
    explicitly.
- `frontend/e2e/app-shell.spec.ts`
  - Updates Playwright workflows for the new onboarding default.
  - Covers hidden first-viewport controls, demo run summary, project setup
    reveal, and advanced/full-evidence reveal.
- `tasks/current-task.md`
  - Records PR B scope and validation gates.
- `progress.md`
  - Records PR B status and validation evidence.
- `session-handoff.md`
  - This handoff record.

## Validation Evidence

- `node scripts\harness-validate.mjs`: passed.
- Browser smoke against temporary `npm run preview`: passed.
- `cd frontend; npm run test`: passed, 21 tests.
- `cd frontend; npm run e2e -- e2e/app-shell.spec.ts`: passed, 16 tests.
- `cd frontend; npm run validate`: passed.
  - `npm run typecheck`: passed.
  - `npm run test`: passed, 21 tests.
  - `npm run build`: passed.
  - `npm run e2e`: passed, 16 Playwright tests.

## Residual Risk

- Existing React `act(...)` warnings still print during `App.test.tsx`; they do
  not fail the suite and predate this onboarding shell work.
- PR B intentionally leaves deeper advanced-workbench extraction for PR C.

## Blockers

- None.

## Next Action

- Run final `git diff --check`, `node scripts\harness-validate.mjs`, and
  `git status --short --branch`; then commit, push, create PR B, wait for all
  required checks, merge it, and update `main` before PR C.
