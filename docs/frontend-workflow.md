# Frontend Build, Test, And Acceptance Workflow

This document defines the development workflow for the future context-eval
local app frontend. It exists so local app server and full Web UI work can build
on a stable frontend quality gate instead of inventing one during feature
implementation.

## Scope

The `frontend/` package is development tooling for the local app UI served by
`context-eval app`. It does not replace the static UI export and does not make Node or npm a runtime requirement for existing context-eval CLI users.

The frontend uses the loopback local app API for config load/save, preflight,
run planning, run lifecycle, log reads, result reads, and exports. It still has
a deterministic fixture fallback so frontend validation can run without a
Python server.

The first full local app workflow is Chinese-first. Visible headings, buttons,
status text, errors, empty states, preflight labels, run labels, result labels,
and export labels should be Chinese while preserving code identifiers, YAML
keys, artifact filenames, and API field names.

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
checks against desktop and narrow viewports. The browser acceptance suite also
starts `context-eval app` against the fixture repository and fake local agent,
then completes the main local workflow through the browser. It does not run a
real external coding agent, install agent CLIs, call hosted services, or use
non-local artifacts.

Acceptance should cover load, edit, save, reload, preflight, plan, run,
results, and exports through the local server API. UI changes must not copy
runner or config parsing logic into the browser.

## Agent Delivery Gate

Every user-visible local app or frontend feature must pass direct
agent-operated browser acceptance before delivery. Automated checks are still
required, but they are not a substitute for the agent opening the actual UI and
using it like a user.

For each feature, the implementing agent must:

- start or connect to the relevant local app or frontend server;
- open the app in a real browser through Codex browser tooling or Playwright;
- click, type, save, run, navigate, and inspect the changed workflow directly;
- verify desktop and narrow viewport layouts, including no horizontal overflow
  or unreadable narrow columns;
- verify the visible copy, labels, errors, empty states, and result summaries
  that the user will see;
- capture screenshots or equivalent browser evidence for the final handoff;
- fix any issue found during this browser pass before claiming the feature is
  ready.

If browser acceptance cannot be completed, the agent must state the blocker and
must not present the feature as fully accepted. Passing `npm run test`,
`npm run build`, or `npm run e2e` alone is not enough for delivery when the
feature has a browser-visible path.

Lightweight motion is allowed for hover, focus, active, loading, progress, and
log-update states. CSS must include a `prefers-reduced-motion` path.

## Build Output

The frontend production build writes static assets to `frontend/dist`. The local
app server serves this directory when it is available and falls back to a small
diagnostic page when it is not.

Built frontend assets are still not added to the Python runtime package data in
this repository state. Source-tree development serves `frontend/dist` directly.

## CI

CI exposes a dedicated `Frontend validation` job. That job installs frontend
dependencies, installs the Chromium browser for Playwright, and runs the root
validation wrapper.

Python tests, local-e2e smoke, skill validation, and package build jobs remain
separate gates. A frontend failure should be visible without weakening existing
Python quality gates.

## Non-Goals

- No no-command-line launcher.
- No hosted dashboard, shared account, remote database, LLM judge, automatic
  agent installation, or agent leaderboard.
