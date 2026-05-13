## Context

context-eval is currently a Python CLI package with static HTML generation and
no bundled frontend build system. The accepted roadmap now includes a local
loopback app and a full browser workflow, but those future changes need a
frontend test and acceptance layer before API and UI work are developed
together.

The repository already uses explicit quality gates for Python tests, local-e2e
smoke tests, skill validation, package build checks, and OpenSpec validation.
The frontend foundation should follow the same pattern: one documented,
script-friendly validation command that CI can run without requiring real
coding agents, hosted services, or local app server behavior.

## Goals / Non-Goals

**Goals:**

- Add a development-only frontend package for the future local app UI.
- Provide deterministic typecheck, unit/component test, build, and browser
  acceptance commands.
- Make the frontend validation gate easy to run locally and in CI.
- Produce build output in a stable location that the later Python local app can
  serve without duplicating frontend source code.
- Document the frontend workflow before local app server and full UI
  implementation begins.

**Non-Goals:**

- Do not implement local app server endpoints in this change.
- Do not replace the existing static UI export mode.
- Do not add a launcher, packaged desktop app, hosted service, remote database,
  leaderboard, LLM judge, or automatic agent installation.
- Do not make Node/npm a runtime requirement for existing CLI users.

## Decisions

1. Use npm with Vite, React, TypeScript, Vitest, and Playwright for the local
   app frontend.

   Vite keeps the development and production build path small, React provides a
   stable component model for the planned multi-view workflow, TypeScript gives
   contract checks before API integration, Vitest covers fast unit/component
   tests, and Playwright provides real browser acceptance. Skill Hub uses Bun
   successfully for its TypeScript CLI, but context-eval is a Python project
   whose frontend should remain consumable by ordinary Node/npm CI and future
   Python packaging steps.

2. Keep frontend tooling development-only for now.

   Existing CLI, runner, report, export, and static UI workflows must continue
   without Node installed. The build output is prepared for future local app
   serving, but source TypeScript is not imported by Python runtime code.

3. Add a single frontend validation entrypoint.

   The frontend package owns `typecheck`, `test`, `build`, `e2e`, and
   `validate` scripts. The repository also provides a wrapper script so CI and
   Windows maintainers have one stable command to run from the project root.

4. Make browser acceptance fixture-backed and server-light.

   The first acceptance check should exercise the built frontend through a
   local preview server with deterministic fixture data. It should prove the
   browser harness, responsive viewports, and smoke workflow work before the
   real local app API exists.

5. Keep future server integration explicit.

   The later local app server PR will decide API details and path safety. This
   change only creates the frontend project, quality gates, docs, and CI
   foundation that server and UI work can rely on.

## Risks / Trade-offs

- [Risk] Adding Node tooling increases repository setup cost. -> Mitigation:
  keep it scoped under `frontend/`, document it as local app development
  tooling, and leave Python CLI validation unchanged.
- [Risk] Playwright can slow CI or fail on browser installation. -> Mitigation:
  run one focused Chromium smoke in a dedicated frontend validation job and keep
  fixtures deterministic.
- [Risk] Frontend APIs could drift before the server exists. -> Mitigation:
  test UI-visible behavior and fixture contracts now, then add API contract
  tests in the local app server PR.
- [Risk] Build output could accidentally enter runtime package scope too early.
  -> Mitigation: document the packaging boundary and only wire runtime package
  data when the local app server consumes the assets.

## Migration Plan

1. Add OpenSpec/docs/tests for the frontend foundation contract.
2. Add the `frontend/` package and root validation wrapper.
3. Wire a dedicated CI job for frontend validation.
4. Update development docs and README with the new optional local app frontend
   gate.
5. Future local app server work can consume the build output and expand browser
   E2E coverage.

Rollback before local app server implementation is straightforward: remove the
frontend package, wrapper script, docs, CI job, and this OpenSpec change without
affecting existing Python CLI behavior.

## Open Questions

- The future local app server PR still needs to choose the Python server stack
  and final static-asset serving path.
- The full Web UI PR still needs a detailed information architecture and
  production layout review.
