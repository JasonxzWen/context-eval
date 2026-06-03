# Codex-First Harness Validation Plan

This file replaces the previous local-app harness reference notes. The active
plan is to make the Codex-first local app path verifiable through deterministic
automation before relying on any live `codex exec` smoke.

## Goal

The default PR gate should prove that context-eval can complete a Codex-shaped
local evaluation without network access, hosted services, provider credentials,
or a real Codex CLI installation.

The critical user journey is:

1. Start from an empty local app workspace.
2. Bootstrap or open a local evaluation project.
3. See the Codex-first run console as the primary operating surface.
4. Run side-effect-free preflight and inspect Codex profile diagnostics.
5. Refresh the run plan and confirm the selected case matrix.
6. Execute a deterministic fake-Codex run.
7. Inspect results, telemetry evidence, artifacts, and exports through the UI.

## Decisions

- Default PR gate includes the Codex-first fake workflow.
- The fake workflow must be deterministic, local-only, and CI-safe.
- The fake Codex runner should mimic the shape of
  `codex exec --json --output-last-message`, including JSONL events and a final
  message artifact.
- Browser E2E is the main acceptance layer for this capability.
- Live `codex exec` remains opt-in only. It must not block default CI or PR
  validation.

## Non-Goals

- Do not run a real external coding agent in default CI.
- Do not require Codex credentials, hosted services, network access, or model
  availability.
- Do not install Codex, Claude Code, Coco, Trae, Harness Hub assets, or target
  repository dependencies.
- Do not create hosted dashboards, remote databases, leaderboards, automatic
  commits, tags, or published packages.
- Do not add an automatic target-repository commit workflow.
- Do not treat fake-Codex success as proof that a user's live Codex
  installation is healthy.

## Harness Architecture

The Codex-first harness has four layers:

| Layer | Gate | Purpose |
| --- | --- | --- |
| Fake Codex runner | deterministic fixture script | Produce Codex-shaped JSONL, final message, logs, repository edits, and telemetry evidence |
| Local app API | pytest service tests | Verify load, save, preflight, run plan, run lifecycle, logs, results, exports, and artifact safety |
| Browser E2E | Playwright | Verify the complete Codex-first user journey across desktop and narrow viewports |
| Root wrapper | `python scripts/validate-codex-first.py` | Provide one local and CI entrypoint with preserved evidence artifacts |

## Fake Codex Contract

The fake runner should be invoked through an agent profile shaped like:

```yaml
agents:
  codex:
    kind: codex-cli
    command: >-
      "{python}" scripts/fake_codex_exec.py --json
      --output-last-message "{output_dir}/codex-final-message.md"
      -C "{workspace}" - < "{prompt_file}"
    telemetry:
      collector: codex-jsonl
      file: codex-events.jsonl
```

The fixture must write:

- `codex-events.jsonl` with token usage, command execution, and tool-call style
  events that match the parser's supported event shape.
- `codex-final-message.md` with a concise completion summary.
- A repository edit that makes the fixture validation command pass.
- stdout and stderr content sufficient for log-tail and artifact inspection.

The harness should also include controlled evidence-gap variants for malformed
JSONL, missing usage, and missing final-message cases. These variants belong in
unit or API tests unless a browser regression specifically depends on them.

## Browser E2E Acceptance

The primary Playwright scenario should run against the real local app server,
not mocked fetch responses. It should cover:

- empty workspace first-run state;
- demo or local project bootstrap;
- Codex-first run console visible before advanced editors;
- preflight readiness and Codex profile diagnostics;
- run plan refresh with selected task, variant, agent, and trial scope;
- explicit run confirmation;
- completed fake-Codex run status;
- result cards with validation, hard-evaluation, and telemetry evidence;
- case detail artifacts for prompt, patch, logs, Codex JSONL, and final
  message;
- JSON or HTML export output;
- desktop and narrow viewport checks for no horizontal overflow and readable
  controls.

Avoid arbitrary sleeps in this suite. Wait on locators, API responses, run
status transitions, and artifact visibility. Retain Playwright traces,
screenshots, and server logs on failure.

## Root Validation Command

Add a single wrapper for this capability:

```bash
python scripts/validate-codex-first.py
```

Expected behavior:

- run the focused Python API/contract tests for the fake-Codex workflow;
- install frontend dependencies and browsers only when requested by flags;
- run the focused Playwright Codex-first project or spec;
- write an evidence bundle under `.context-eval/verification/codex-first/`;
- emit a concise pass/fail summary with paths to artifacts.

The CI job should call the same wrapper. The wrapper should have an opt-in flag
for live Codex smoke, but CI must not enable it by default:

```bash
python scripts/validate-codex-first.py --live-codex
```

## CI Gate

Add a dedicated CI job named `Codex-first validation`.

The job must:

- run on Ubuntu with Python and Node installed;
- install the Python package in editable mode;
- install frontend dependencies and Chromium;
- run the root Codex-first validation wrapper;
- upload the evidence bundle when the job fails.

The job must not:

- call live `codex exec`;
- require provider credentials;
- call hosted services;
- reuse an unrelated local server port;
- weaken the existing Python, local-e2e, frontend, skill, or package-build
  gates.

## Aligned Implementation Answers

1. The first browser E2E path uses the existing "Try demo" bootstrap so the
   validation covers the real empty-workspace first-run journey.
2. The fake-Codex runner is generated into the demo repository as
   `scripts/example_agent.py`, keeping the fixture self-contained and avoiding
   a second demo setup path.
3. The root wrapper runs focused Python Codex contracts, frontend typecheck,
   production build, and the focused Playwright Codex-first scenario. The
   broader `npm run validate` gate remains separate.
4. CI keeps command logs, the local app server log, run directory artifacts, and
   Playwright artifacts under the evidence directory; Playwright traces and
   screenshots are retained on failure.
5. Evidence-gap browser coverage is not in the MVP path. Malformed JSONL,
   missing usage, and missing final-message behavior stay in API/unit tests
   unless a user-visible regression depends on them.
6. The new CI job should stay short enough for default PR feedback. The focused
   local run targets a few minutes, not the full frontend validation cost plus a
   live external-agent smoke.

## MVP Acceptance

The MVP is accepted when a clean CI environment can run the default
Codex-first validation job and prove, without live Codex, that configuration,
preflight, run planning, execution, telemetry parsing, result review, artifact
inspection, and export all work through the local app's user-facing path.
