# Progress

## Current State

- Active task is the post-PR-D onboarding shell follow-up on
  `codex/onboarding-turn-summary`.
- PR A (#62), PR B (#63), PR C (#64), and PR D (#65) are merged into `main`.
- `tasks/current-task.md` records the current follow-up scope, allowed paths,
  forbidden paths, acceptance criteria, and validation commands.
- The simplified onboarding conclusion now includes structured
  `interaction_turn_count` in both scoring and visible result comparison.
- Operation complexity scoring now uses collected tool calls plus collected
  interaction turns, without treating missing turn telemetry as zero.

## Current Follow-Up Validation

- RED: `npm run test -- src/scoring.test.ts` failed before implementation
  because lower interaction turns did not affect the comparison verdict.
- GREEN: `npm run test -- src/scoring.test.ts` passed: 8 tests.
- RED: the onboarding App test failed before UI implementation because
  `交互轮次` was absent from the simplified conclusion.
- GREEN: `npm run test -- src/App.test.tsx -t "runs the demo from onboarding"`
  passed after adding the metric display.
- `npx playwright test e2e/app-shell.spec.ts -g "empty workspace starts at first-run choices and bootstraps demo"`
  passed after rebuilding `frontend/dist`: 2 tests.
- `cd frontend; npm run test` passed: 23 tests.
- `cd frontend; npm run validate` passed:
  - TypeScript check passed.
  - Vitest passed: 23 tests.
  - Vite build passed.
  - Playwright E2E passed: 16 tests.
- `node scripts\harness-validate.mjs` passed.
- `git diff --check` passed.
- Vitest still prints existing React `act(...)` warnings in `App.test.tsx`;
  the suite passes and these warnings predate this follow-up.

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

- Review final diff, commit, push, create the follow-up PR, wait for checks,
  merge, and update `main`.
