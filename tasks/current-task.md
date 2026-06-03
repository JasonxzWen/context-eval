# Current Task

## Goal

Implement PR B for the context-eval onboarding shell plan: make the default
frontend entry point an onboarding home that guides a new user through one demo
or configured evaluation run, then shows a concise score summary before the old
workbench is opened.

## Assumptions

- PR A is merged into `main`; `frontend/src/scoring.ts` is available.
- The repository is on a fresh branch from latest `main`:
  `codex/onboarding-home-shell`.
- The onboarding shell should reuse existing backend APIs and run state.
- Small, scoped CSS additions are allowed for the new shell; broad CSS
  redesign is deferred.

## Non-goals

- Do not implement PR C advanced workbench extraction as a full refactor.
- Do not implement PR D Codex interaction turn counting.
- Do not change backend telemetry collection or result persistence.
- Do not rewrite the existing results workbench beyond the minimum integration
  needed to hide it by default.

## Worktree / Branch

- Worktree: `C:\Users\Admin\.codex\worktrees\a3f4\context-eval`
- Branch: `codex/onboarding-home-shell`

## Allowed paths

- `frontend/src/App.tsx`
- `frontend/src/App.test.tsx`
- `frontend/src/components/OnboardingHome.tsx`
- `frontend/src/components/RunScoreSummary.tsx`
- `frontend/src/styles.css`
- `frontend/e2e/app-shell.spec.ts`
- `progress.md`
- `session-handoff.md`
- `tasks/current-task.md`

## Forbidden paths

- `context_eval/`
- Backend tests under `tests/`
- Harness install files outside task/progress/handoff records.
- Broad CSS rewrites unrelated to the new onboarding shell.

## Acceptance criteria

- All users land on `OnboardingHome` by default instead of the old workbench.
- Empty workspaces show one primary action: `运行一次 demo 评测`.
- Configured workspaces that have not run show one primary action:
  `运行一次评测`.
- Running state shows linear progress and does not expose the old workbench by
  default.
- Completed state shows `RunScoreSummary`.
- The summary shows `综合分`, baseline score, experiment score, recommended
  variant or `无明显胜出`, duration, tokens, tool calls, changed files, and
  evidence confidence.
- Secondary actions exist for `我已经有项目`, `高级工作台`, and
  `查看完整证据`, without taking primary visual priority.
- Local path, Git URL, YAML, task editor, command template, and old workbench
  controls are hidden on the default first viewport.
- `查看完整证据` or `高级工作台` reveals the existing detailed workbench.
- Tests cover the default onboarding state, demo run path, score summary, and
  advanced/full-evidence reveal behavior.

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
