# Current Task

## Goal

Implement the post-PR-D onboarding shell follow-up: include structured Codex
interaction turn counts in the simplified run conclusion and in the operation
complexity scoring path.

## Assumptions

- PR A, PR B, PR C, and PR D are merged into `main`.
- The repository is on a fresh branch from latest `main`:
  `codex/onboarding-turn-summary`.
- `interaction_turn_count` is already available on `ResultCase` from structured
  Codex JSONL telemetry.
- Missing turn telemetry must remain unavailable in UI and evidence notes; do
  not infer it from stdout or stderr.

## Non-goals

- Do not change backend telemetry collection.
- Do not change the onboarding shell layout beyond the metric display hook.
- Do not make broad CSS or visual redesign changes.
- Do not change scoring weights; keep operation complexity at weight 8.

## Worktree / Branch

- Worktree: `C:\Users\Admin\.codex\worktrees\a3f4\context-eval`
- Branch: `codex/onboarding-turn-summary`

## Allowed paths

- `frontend/src/scoring.ts`
- `frontend/src/scoring.test.ts`
- `frontend/src/components/RunScoreSummary.tsx`
- `frontend/src/App.test.tsx`
- `frontend/e2e/app-shell.spec.ts`
- `progress.md`
- `session-handoff.md`
- `tasks/current-task.md`

## Forbidden paths

- Backend telemetry/model/export files.
- Broad frontend style rewrites.
- Harness install files outside task/progress/handoff records.
- Package metadata changes unless validation proves they are required.

## Acceptance criteria

- Operation complexity scoring accounts for structured interaction turn counts
  together with tool call counts.
- Missing structured turn counts remain unknown and create an evidence gap
  instead of being treated as zero.
- The simplified `RunScoreSummary` conclusion shows interaction turns for
  baseline and comparison cases.
- The default onboarding E2E path asserts that interaction turns are visible in
  the simplified conclusion before the advanced workbench is revealed.
- Existing App and Playwright workflows continue to pass.

## Validation commands

- `cd frontend; npm run test`
- `cd frontend; npm run build`
- `cd frontend; npx playwright test e2e/app-shell.spec.ts`
- `cd frontend; npm run validate`
- `node scripts\harness-validate.mjs`
- `git diff --check`
- `git status --short --branch`

## Parallel writes

- Default: blocked for this task.
- Use read-only parallel commands only for inspection or validation.

## Handoff requirements

- Update `progress.md`.
- Update `session-handoff.md`.
- Run `node scripts/harness-validate.mjs`.
- Record validation evidence and the next concrete action before handoff.
