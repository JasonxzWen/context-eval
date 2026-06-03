# Session Handoff

## Current Status

- Current branch: `codex/onboarding-advanced-workbench`.
- Branch was created from latest `main` after PR #63 merged.
- Active task is PR C: old detailed workbench downgrade via an explicit
  `AdvancedWorkbench` boundary.
- PR C implementation is complete locally and validated; next action is final
  diff hygiene, commit, push, open PR, wait for checks, and merge before
  starting PR D.

## Changed Files

- `frontend/src/components/AdvancedWorkbench.tsx`
  - New thin component boundary for the existing detailed workbench.
  - Preserves the existing `content-grid` layout and exposes
    `data-testid="advanced-workbench"`.
- `frontend/src/App.tsx`
  - Imports and renders `AdvancedWorkbench` only when `workbenchVisible` is
    true.
  - Leaves all existing workbench internals in place to keep PR C scoped.
- `frontend/src/App.test.tsx`
  - Asserts the advanced workbench boundary is absent on default onboarding.
  - Asserts full-evidence and advanced-workbench reveal paths render the
    boundary.
- `frontend/e2e/app-shell.spec.ts`
  - Asserts `advanced-workbench` is absent before evidence reveal and visible
    after reveal.
- `tasks/current-task.md`
  - Records PR C scope and validation gates.
- `progress.md`
  - Records PR C status and validation evidence.
- `session-handoff.md`
  - This handoff record.

## Validation Evidence

- `cd frontend; npm run validate`: passed.
  - `npm run typecheck`: passed.
  - `npm run test`: passed, 21 tests.
  - `npm run build`: passed.
  - `npm run e2e`: passed, 16 Playwright tests.

## Residual Risk

- Existing React `act(...)` warnings still print during `App.test.tsx`; they do
  not fail the suite and predate this refactor.
- PR C intentionally avoids a large prop extraction of every old workbench
  subcomponent; it creates a stable boundary first. Deeper cleanup can happen
  separately if needed.

## Blockers

- None.

## Next Action

- Run final `git diff --check`, `node scripts\harness-validate.mjs`, and
  `git status --short --branch`; then commit, push, create PR C, wait for all
  required checks, merge it, and update `main` before PR D.
