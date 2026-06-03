# Current Task

## Goal

Implement PR C for the context-eval onboarding shell plan: give the old
detailed workbench an explicit `AdvancedWorkbench` boundary so it remains a
secondary mode and is not part of the default onboarding viewport.

## Assumptions

- PR A is merged into `main`; `frontend/src/scoring.ts` is available.
- PR B is merged into `main`; `OnboardingHome` and `RunScoreSummary` are the
  default entry point.
- The repository is on a fresh branch from latest `main`:
  `codex/onboarding-advanced-workbench`.
- This PR should be a small structural boundary and test hardening step, not a
  visual redesign.

## Non-goals

- Do not implement PR D Codex interaction turn counting.
- Do not change backend telemetry collection or result persistence.
- Do not rewrite task, variant, agent, or result internals.
- Do not make broad CSS changes.

## Worktree / Branch

- Worktree: `C:\Users\Admin\.codex\worktrees\a3f4\context-eval`
- Branch: `codex/onboarding-advanced-workbench`

## Allowed paths

- `frontend/src/App.tsx`
- `frontend/src/App.test.tsx`
- `frontend/src/components/AdvancedWorkbench.tsx`
- `frontend/e2e/app-shell.spec.ts`
- `progress.md`
- `session-handoff.md`
- `tasks/current-task.md`

## Forbidden paths

- `context_eval/`
- Backend tests under `tests/`
- Harness install files outside task/progress/handoff records.
- Broad CSS rewrites or visual redesign work.

## Acceptance criteria

- The old workbench is represented by an `AdvancedWorkbench` component
  boundary.
- `AdvancedWorkbench` is not rendered on the default onboarding viewport.
- Clicking `高级工作台` renders `AdvancedWorkbench` and preserves the existing
  detailed workbench behavior.
- Clicking `查看完整证据` after a completed run renders `AdvancedWorkbench` and
  preserves the existing detailed results behavior.
- Default onboarding tests assert the old workbench boundary is absent until a
  reveal action.
- Existing App and Playwright workflows continue to pass.

## Validation commands

- `node scripts\harness-validate.mjs`
- `cd frontend; npm run test`
- `cd frontend; npm run validate`
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
