# Frontend Build, Test, And Acceptance Workflow

This document defines the development workflow for the future context-eval
local app frontend. It exists so local app server and full Web UI work can build
on a stable frontend quality gate instead of inventing one during feature
implementation.

## Scope

The `frontend/` package is development tooling for the planned local app UI. It
does not implement the local app server, does not replace the static UI export,
and does not make Node or npm a runtime requirement for existing context-eval
CLI users.

The current frontend shell uses deterministic fixture data. Later local app
server work will replace those fixtures with loopback API calls covered by API
contract tests.

## Toolchain

- React + Vite + TypeScript for the browser app shell.
- Vitest and Testing Library for unit and component tests.
- Playwright for browser acceptance across desktop and narrow viewports.
- npm for dependency installation and script execution.

The repository pins the frontend Node line with `.node-version`. Python remains
the runtime requirement for the existing CLI package.

## Commands

Run commands from `frontend/` when working directly on the UI:

```bash
npm run typecheck
npm run test
npm run build
npm run e2e
npm run validate
```

From the repository root, use the wrapper command:

```powershell
python scripts\validate-frontend.py --install --install-browsers
```

On Linux CI, the same wrapper can also request Playwright system dependencies:

```bash
python scripts/validate-frontend.py --install --install-browsers --install-system-deps
```

The combined validation command runs typecheck, tests, build, and browser
acceptance in that order.

## Browser Acceptance

Playwright serves the production build with Vite preview and runs Chromium smoke
checks against desktop and narrow viewports. The acceptance tests use
deterministic local fixtures only. They do not run coding agents, install agent
CLIs, call hosted services, or depend on a local app server.

## Build Output

The frontend production build writes static assets to `frontend/dist`. This is a
stable local output directory for future local app server work to serve
explicitly.

This foundation change intentionally leaves Python package data unchanged. Built
frontend assets are not added to the runtime package until a later local app
server change consumes them.

## CI

CI exposes a dedicated `Frontend validation` job. That job installs frontend
dependencies, installs the Chromium browser for Playwright, and runs the root
validation wrapper.

Python tests, local-e2e smoke, skill validation, and package build jobs remain
separate gates. A frontend failure should be visible without weakening existing
Python quality gates.

## Non-Goals

- No local app server endpoints.
- No complete Web UI workflow.
- No no-command-line launcher.
- No hosted dashboard, shared account, remote database, LLM judge, automatic
  agent installation, or agent leaderboard.
