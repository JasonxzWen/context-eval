# Decisions

## Active Decisions

- Date: 2026-06-05
- Decision: Use `harness-hub check . --json` as the standard read-only startup
  sniff for Harness Hub package releases and target managed-component updates.
- Rationale: `@jasonwen/harness-hub@0.1.13` reports CLI package status against
  npm latest separately from target lock/component status, which matches the
  requested new package release sniffing capability.
- Alternatives considered: Use `status . --json` only; rejected because it is a
  detailed target audit and does not foreground CLI package release status as
  clearly as `check`.
- Status: accepted for this task.
- State-file impact: active task, progress, and handoff now live under ignored
  `.harness-hub/state/` files.
- Follow-up: Use `npx -y @jasonwen/harness-hub@latest check . --json` at future
  task startup.

## Resolved Decisions

- Date: 2026-06-05
- Decision: Keep Harness Hub active state under ignored `.harness-hub/state/`
  instead of tracked root `progress.md`, `session-handoff.md`, and
  `tasks/current-task.md`.
- Rationale: `harness:minimal@0.5.2` moved volatile task state out of tracked
  root files while retaining stable tracked harness rules and validation.
- Status: resolved by lock-backed update.
- Follow-up: Keep handoff evidence in `.harness-hub/state/session-handoff.md`.

## Decision Template

- Date:
- Decision:
- Rationale:
- Alternatives considered:
- Status:
- State-file impact:
- Follow-up:
