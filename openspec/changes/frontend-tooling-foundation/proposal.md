## Why

The planned local app and full web UI need a reliable frontend build, test, and
browser acceptance foundation before server endpoints and product workflows are
implemented. Adding that foundation now prevents the local app work from mixing
runtime safety decisions with late test-harness setup.

## What Changes

- Add a dedicated frontend tooling foundation for the future local app UI.
- Define a TypeScript frontend package with typecheck, unit test, build, and
  browser acceptance gates.
- Add repository-level validation commands and CI wiring for the frontend gate.
- Document how frontend assets are built, tested, and later consumed by the
  Python local app.
- Keep static UI export and existing Python CLI behavior unchanged.
- Do not implement the local app server, launcher, or complete Web UI workflow
  in this change.

## Capabilities

### New Capabilities

- `frontend-tooling`: Frontend package structure, deterministic build output,
  unit/component testing, browser acceptance checks, CI validation, and
  development workflow documentation for the future local app UI.

### Modified Capabilities

- None. This change prepares frontend engineering infrastructure without
  changing the runtime requirements of the existing CLI, runner, reports,
  exports, or static UI.

## Impact

- Adds development-only Node/npm tooling for the local app frontend.
- Adds frontend validation scripts and CI jobs.
- Adds docs and tests that establish the expected frontend quality gates before
  local app server and full Web UI implementation begins.
- Preserves local-only, artifact-based product boundaries and avoids any hosted
  service, leaderboard, automatic agent installation, or automatic commit
  behavior.
