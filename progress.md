# Progress

## Current State

- The context-eval onboarding shell refactor plan from the June 3 handoff is
  complete on `main`.
- The repository is synced to the latest merged `main`.
- Harness state files are present and current:
  - `progress.md`
  - `session-handoff.md`
  - `tasks/current-task.md`
- There is no active implementation task remaining from the onboarding shell
  plan.

## Completed Onboarding Shell PRs

- PR #62: scoring engine and unit tests.
- PR #63: default onboarding home and simplified score summary.
- PR #64: advanced workbench boundary for the old detailed UI.
- PR #65: structured Codex interaction turn count across backend models,
  runner propagation, exports, frontend types, and result details.
- PR #66: interaction turn counts in simplified onboarding scoring and summary.

## Verified Product Requirements

- All users enter the onboarding home by default.
- Empty workspaces show the primary `运行一次 demo 评测` action and hide local
  project, Git URL, YAML, task editor, and command-template controls.
- Demo runs bootstrap, plan, execute, and then show the simplified conclusion.
- The simplified conclusion shows `综合分`, baseline score, experiment score,
  recommendation or no-clear-winner state, duration, tokens, tool calls,
  interaction turns, changed files, and evidence confidence.
- `高级工作台` / `查看完整证据` reveal the old detailed workbench only after the
  user asks for it.
- Structured Codex turn counts come only from JSONL events; missing values stay
  unavailable and lower evidence confidence where relevant.

## Validation Evidence

- PR #66 local validation:
  - `npm run test -- src/scoring.test.ts`: 8 tests passed.
  - `npm run test -- src/App.test.tsx -t "runs the demo from onboarding"`:
    passed.
  - `npx playwright test e2e/app-shell.spec.ts -g "empty workspace starts at first-run choices and bootstraps demo"`:
    2 tests passed after `npm run build`.
  - `cd frontend; npm run test`: 23 tests passed.
  - `cd frontend; npm run validate`: typecheck, unit tests, build, and 16 E2E
    tests passed.
  - `node scripts\harness-validate.mjs`: passed.
  - `git diff --check`: passed.
- PR #66 remote checks passed: Codex-first validation, Frontend validation,
  Local E2E smoke, Package build, Python 3.11/3.12 on Ubuntu and Windows, and
  Skill validation.

## Harness Install State

- Harness Hub minimal harness has been installed in `D:\context-eval`.
- The install created root harness state files, `scripts/harness-validate.mjs`,
  `.harness-hub/lock.json`, and the standard `skills/` tree.
- `.harness-hub/reports/` is ignored so generated install reports stay local.
- README, configuration docs, and Harness Hub provenance docs describe the
  installed standard minimal harness boundary.
- Ruff excludes the root `skills/` capability tree, and package artifact
  inspection rejects `.harness-hub/`, `skills/`, and root harness state files.

## Next Action

- No onboarding-shell follow-up remains. Open a new task only for new product
  scope or regressions discovered after use.
