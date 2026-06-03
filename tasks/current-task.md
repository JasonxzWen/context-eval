# Current Task

## Goal

Install the standard Harness Hub minimal harness into this repository and report
the resulting local harness environment.

## Assumptions

- The target is the current repository at `D:\context-eval`.
- Harness Hub should manage the standard skill set and minimal root harness files.

## Non-goals

- Do not change `context_eval` runtime behavior.
- Do not create commits, tags, releases, or package artifacts.
- Do not run live external coding agents.

## Worktree / Branch

- Worktree: `D:\context-eval`
- Branch: `main`

## Allowed paths

- `.harness-hub/`
- `.gitignore`
- `AGENTS.md`
- `clean-state-checklist.md`
- `definition-of-done.md`
- `docs/architecture.md`
- `docs/configuration.md`
- `docs/development-plan.md`
- `docs/harness-hub-import.md`
- `docs/release-checklist.md`
- `feature_list.json`
- `progress.md`
- `pyproject.toml`
- `README.md`
- `scripts/inspect-package-artifacts.py`
- `scripts/harness-validate.mjs`
- `session-handoff.md`
- `skills/`
- `tasks/current-task.md`
- `tests/test_package_artifact_inspection.py`
- `tests/test_project_readiness.py`

## Forbidden paths

- `context_eval/`
- `frontend/`
- `tests/`
- Runtime implementation files outside the harness validation script.

## Acceptance criteria

- Harness Hub `init-harness --target standard` has completed successfully.
- Required harness files are present.
- Standard skills are installed and lock-managed.
- Generated Harness Hub reports are kept out of Git.
- Harness validation passes.
- README, configuration docs, provenance docs, and readiness tests reflect the
  installed standard minimal harness boundary.
- Ruff and release artifact inspection keep Harness Hub capabilities outside
  the runtime package surface.
- Local Git status clearly shows the new harness files.

## Validation commands

- `npx -y @jasonwen/harness-hub@latest validate-harness "D:\context-eval" --json`
- `npx -y @jasonwen/harness-hub@latest status "D:\context-eval" --json`
- `npx -y @jasonwen/harness-hub@latest update "D:\context-eval" --dry-run --json`
- `node scripts\harness-validate.mjs`
- `ruff check .`
- `python -m pytest tests/test_package_artifact_inspection.py -q`
- `python -m pytest tests/test_project_readiness.py -q`
- `git status --short --branch`

## Parallel writes

- Default: blocked for this task.
- Allowed only with independent worktrees or branches, non-overlapping paths, independent validation, and one integration review point.

## Handoff requirements

- Update `progress.md`.
- Update `session-handoff.md`.
- Run `node scripts/harness-validate.mjs`.
