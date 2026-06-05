# Current Task

## Goal

Update the repository's installed Harness Hub state so maintainers can sniff new
Harness Hub package releases and target managed-component updates from the
startup path.

## Assumptions

- The user means the project-local Harness Hub installation in this repository,
  not upstream Harness Hub source development.
- `@jasonwen/harness-hub@0.1.13` is the npm latest version observed on
  2026-06-05.
- `harness-hub check . --json` is the intended read-only release sniffing
  command because it reports CLI package status and target managed-component
  status separately.

## Non-goals

- Do not change `context_eval/` runtime behavior.
- Do not change package metadata or publish artifacts.
- Do not import Harness Hub npm CLI lifecycle source code.
- Do not create, push, or merge a PR in this session.

## Worktree / Branch

- Worktree: `C:\Users\Admin\.codex\worktrees\5bcb\context-eval`
- Branch: `codex/harness-hub-release-sniffing`

## Allowed paths

- `.harness-hub/**`
- `AGENTS.md`
- `clean-state-checklist.md`
- `definition-of-done.md`
- `evaluator-rubric.md`
- `feature_list.json`
- `quality-document.md`
- `scripts/harness-validate.mjs`
- `scripts/inspect-package-artifacts.py`
- `skills/delivery-workflow/**`
- `skills/effective-interact/**`
- `docs/**`
- `README.md`
- `tests/test_project_readiness.py`
- `tests/test_package_artifact_inspection.py`

## Forbidden paths

- `context_eval/**`
- `frontend/**`
- `pyproject.toml`
- `CHANGELOG.md`
- Release publish credentials, tags, or remote package registry writes.

## Acceptance criteria

- Harness Hub managed update applies without `--force`.
- `harness:minimal` is updated to `0.5.2`, `delivery-workflow` to `0.1.1`, and
  `effective-interact` to `0.2.1` in `.harness-hub/lock.json`.
- The standard startup path documents and validates `harness-hub check . --json`
  as read-only new package release sniffing.
- Active task, decisions, progress, and handoff move to ignored
  `.harness-hub/state/` files.
- Package boundary docs and tests reject new root harness files and hidden
  Harness Hub state from runtime package artifacts.
- No product runtime or frontend behavior changes.

## Standard startup path

- Run `npx -y @jasonwen/harness-hub@latest check . --json` before implementation
  to sniff CLI package release status and target managed-component updates.
- Run `node scripts\harness-validate.mjs`.
- Review `.harness-hub/state/current-task.md`, `.harness-hub/state/progress.md`,
  `.harness-hub/state/decisions.md`, `.harness-hub/state/session-handoff.md`,
  `feature_list.json`, and `git status --short`.

## Validation commands

- `npx -y @jasonwen/harness-hub@latest check . --json`
- `npx -y @jasonwen/harness-hub@latest update . --dry-run --json`
- `npx -y @jasonwen/harness-hub@latest status . --json`
- `npx -y @jasonwen/harness-hub@latest validate-harness . --json`
- `node scripts\harness-validate.mjs`
- `python -m pytest tests/test_project_readiness.py tests/test_package_artifact_inspection.py`
- `git diff --check`
- `git status --short --branch`

## Validation tiers

- P0: Harness Hub `check`, `update --dry-run`, `validate-harness`, local
  `harness-validate`, targeted readiness/package tests, and `git diff --check`.
- P1: `harness-hub status . --json` to audit all managed component states.
- P2: Full repository pytest and frontend validation are deferred unless touched
  files expand into runtime or Web behavior.

## Web browser acceptance

- Not applicable. This task has no Web user-visible behavior and requires no
  agent-run browser evidence.

## Runtime signals

- No app server, runtime logs, network traces, or browser console signals are
  expected.
- npm registry access is used only by read-only Harness Hub package sniffing.

## PR closeout

- Draft PR: `https://github.com/JasonxzWen/context-eval/pull/68`.
- Mergeability: `MERGEABLE` from `gh pr view 68 --json mergeable`.
- CI/check-run status: in progress at PR creation time.
- Conflict status: no conflict reported by GitHub mergeability.
- Branch protection blockers: pending CI/check-run completion.

## Checkpoint policy

- Commit created for PR publication.
- Commit before handoff update: `9d16798b7381fac8f54b8774a737823aad929c8e`.
- Final commit is recorded in `.harness-hub/state/session-handoff.md`.

## Spec updates

- No OpenSpec change is required because this is harness maintenance and docs
  synchronization, not context-eval product behavior.

## Decision log

- Record the state-file migration and package sniffing command in
  `.harness-hub/state/decisions.md`.

## Parallel writes

- Parallel writes are blocked.
- Read-only parallel work is allowed for research, review, log analysis, and
  validation only.

## Handoff requirements

- Update `.harness-hub/state/progress.md`,
  `.harness-hub/state/session-handoff.md`, and
  `.harness-hub/state/decisions.md`.
- Include changed files, validation evidence, skipped checks, blockers, residual
  risk, checkpoint commit status, and next concrete action.
