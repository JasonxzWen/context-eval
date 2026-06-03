# Current Task

## Goal

Implement PR A for the context-eval onboarding shell plan: add a frontend
scoring engine and focused unit tests that can compare completed run results
before the onboarding UI is rebuilt.

## Assumptions

- The branch starts from the latest `origin/main`, including the Harness Hub
  minimal harness files.
- The scoring engine is frontend-only and consumes the existing `ResultCase`
  and `ResultsPayload` types.
- PR A must be completed, validated, opened as a PR, and merged before PR B
  onboarding shell work begins.

## Non-goals

- Do not make broad CSS changes.
- Do not rebuild the onboarding home, result cards, or advanced workbench in
  this PR.
- Do not change backend telemetry collection or add Codex turn counting in
  this PR.

## Worktree / Branch

- Worktree: `C:\Users\Admin\.codex\worktrees\a3f4\context-eval`
- Branch: `codex/onboarding-score-shell`

## Allowed paths

- `frontend/src/scoring.ts`
- `frontend/src/scoring.test.ts`
- `frontend/src/types.ts`
- `progress.md`
- `session-handoff.md`
- `tasks/current-task.md`

## Forbidden paths

- `frontend/src/App.tsx`
- `frontend/src/styles.css`
- `frontend/src/components/`
- `context_eval/`
- `tests/`
- Runtime implementation files outside the frontend scoring module.

## Acceptance criteria

- `scoreRunResults(results: ResultsPayload | ResultCase[])` exists.
- `ResultCase` exposes the backend-provided `trial_index` field for structured
  grouping.
- Scores include correctness, speed, cost, operation complexity, and change
  scope components.
- Correctness-failed variants cannot win because they are faster or cheaper.
- Variants are compared within the same `task_id + agent_name + trial_index`
  group.
- Passing variants use duration, tokens, tool calls, and changed files to break
  meaningful ties.
- Score deltas below 5 points report no clear winner.
- Missing telemetry lowers confidence and leaves unavailable resource metrics
  unscored rather than guessing zeroes.
- Hard and soft evaluation scores contribute to correctness.
- The scoring module is validated by focused unit tests and the full frontend
  validation gate.

## Validation commands

- `node scripts\harness-validate.mjs`
- `cd frontend; npm run test -- src/scoring.test.ts`
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
