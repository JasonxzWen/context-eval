# Current Task

## Goal

Record completion of the context-eval onboarding shell plan from the June 3
handoff. No active onboarding-shell implementation task remains.

## Assumptions

- PR #62, PR #63, PR #64, PR #65, and PR #66 are merged into `main`.
- The repository has the Harness Hub state files and uses them for task
  tracking.
- This closeout record does not add product behavior or code changes.

## Non-goals

- Do not change frontend or backend behavior.
- Do not change package metadata.
- Do not start a new product scope.

## Worktree / Branch

- Worktree: `C:\Users\Admin\.codex\worktrees\a3f4\context-eval`
- Branch: `codex/onboarding-plan-closeout`

## Allowed paths

- `progress.md`
- `session-handoff.md`
- `tasks/current-task.md`

## Forbidden paths

- Frontend source and tests.
- Backend source and tests.
- Package metadata.
- Harness install files outside task/progress/handoff records.

## Acceptance criteria

- Harness state records that the onboarding shell plan is complete.
- Completed PRs are listed with their scope.
- Current invariants are listed for future work.
- Validation evidence from the final implementation PR is recorded.
- No remaining onboarding-shell development step is listed as pending.

## Validation commands

- `node scripts\harness-validate.mjs`
- `git diff --check`
- `git status --short --branch`

## Parallel writes

- Default: blocked for this closeout task.
- Use read-only parallel commands only for inspection or validation.

## Handoff requirements

- Keep `progress.md` in completed state.
- Keep `session-handoff.md` in completed state.
- Keep this file in completed state while preserving harness-required section
  markers.

## Completed PRs

- PR #62: scoring engine and unit tests.
- PR #63: onboarding shell and simplified score summary.
- PR #64: advanced workbench boundary.
- PR #65: structured Codex interaction turn count.
- PR #66: interaction turns in onboarding summary scoring and display.

## Current Invariants

- Default users enter the onboarding home.
- Empty workspaces expose one primary demo action and hide advanced setup.
- Demo completion shows a simplified conclusion before detailed evidence.
- Detailed results and legacy configuration appear only through
  `高级工作台` or `查看完整证据`.
- Composite scoring accounts for correctness, speed, cost, operation
  complexity, change scope, and evidence confidence.
- Operation complexity includes collected tool calls and structured interaction
  turns.
- Missing structured turn telemetry is not inferred from logs and remains
  unavailable in UI/evidence notes.
