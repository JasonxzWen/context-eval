## Why

The packaged `context-eval-app` entry point is now part of the release-facing
local app path, but the release install smoke still proves only the installed
`context-eval` CLI. Before future launcher packaging work, the release gate
should verify that the installed launcher entry can be resolved and can perform
a local startup preflight without opening a browser or serving indefinitely.

## What Changes

- Add a launcher startup preflight mode for `context-eval-app` that validates
  workspace, config, log path, loopback host, port, and frontend availability,
  then exits without opening a browser or running the local app server.
- Extend the release candidate install smoke to cover the installed
  `context-eval-app` script with `--no-browser`, `--port 0`, and the startup
  preflight mode.
- Document the launcher install-smoke acceptance step in README and release
  checklist guidance.
- Preserve the manual tag and publish boundary.

## Capabilities

### New Capabilities

- `launcher-installed-smoke`: Installed package smoke coverage for the packaged
  local app launcher entry point.

### Modified Capabilities

- None. Existing local app and release docs are updated to reference the new
  smoke gate, but no archived main specs exist yet.

## Impact

- `context_eval/launcher.py`: adds a non-serving preflight path for the
  packaged launcher command.
- `scripts/install-smoke-artifacts.py`: runs the launcher preflight through the
  installed `context-eval-app` console script.
- `docs/release-checklist.md`, `docs/release-candidate-install-smoke.md`,
  `docs/local-app-workflow.md`, `README.md`, and `CHANGELOG.md`: document the
  launcher acceptance coverage and retain local-only/manual-publish boundaries.
- Tests cover the launcher CLI behavior and install smoke plan before
  implementation.
