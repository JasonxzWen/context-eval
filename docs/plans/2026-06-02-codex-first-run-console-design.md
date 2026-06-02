# Codex-first Run Console Design

## Goal

Make the local frontend optimize for a first successful Codex-backed evaluation run.
The first screen should answer four questions quickly:

- Which project is open?
- Which Codex profile will run?
- Is the profile observable enough to trust results?
- What is the next action: fix setup, refresh plan, run, or inspect evidence?

## Decisions

- Use a run-console-first layout.
- Keep task, variant, agent, and raw YAML editors, but move them behind an advanced configuration section.
- Treat stable fake-agent E2E as the MVP bootstrap gate.
- Keep real `codex exec` self-evaluation as an optional local smoke path, not a required CI gate.
- Do not rewrite all frontend state in this iteration. Extract only small presentational components where it lowers risk.

## Proposed Interface

The first non-empty screen is a compact operating console:

1. Project and environment status.
2. Codex profile summary, command shape, telemetry collector, and warnings.
3. Run scope and plan count.
4. Primary actions: refresh plan, start run, stop run, inspect results.
5. Result evidence entry point after a run completes.

Advanced configuration stays available below the console for users who need detailed task, context, agent, or YAML edits.

## Test Strategy

- Fix Playwright so it does not silently reuse an unrelated server on port `4173`.
- Keep Vitest coverage for Codex telemetry save payloads.
- Add or adjust Playwright coverage for the fake-agent bootstrap path and run-console visibility.
- Report real Codex smoke as manual or opt-in if it depends on local credentials.

## Out Of Scope

- Full `App.tsx` reducer/hook rewrite.
- New backend endpoints beyond fields already exposed by preflight and run-plan.
- Mandatory live Codex execution in automated E2E.
