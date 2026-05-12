# Local E2E CI Smoke And Test Taxonomy

This spec defines a higher-level local CI gate for context-eval. The goal is to
make CI prove that the installed CLI can run a realistic local artifact workflow,
without changing the product boundary into a hosted benchmark or managed agent
service.

This is a local artifact-based quality gate. It is not a benchmark or
leaderboard, and it should be maintained with the same local-only boundaries as
the rest of context-eval.

## Goal

The repository already has broad pytest coverage, including unit tests,
integration-style runner tests, CLI tests, release artifact checks, and static
UI HTML checks. The missing layer is a clearly named local-e2e smoke test that
executes the installed CLI across the main user workflow:

1. create or reuse a fixture repository;
2. run a fake local agent through `context-eval run`;
3. regenerate `context-eval report`;
4. write deterministic `context-eval export` outputs;
5. render `context-eval ui`;
6. assert the resulting local artifacts are parseable and self-contained.

## Test Taxonomy

- Unit tests: pure model, parser, normalization, and formatting behavior.
- Integration tests: runner, adapter, config, reporting, export, and package
  build behavior using temporary local files and fixture repositories.
- Local-e2e smoke: one installed CLI workflow using a fixture repository and a
  fake local agent. It should verify the product path from command invocation to
  recorded artifacts.
- Optional browser smoke: a follow-up Playwright check against generated static
  HTML when UI behavior changes. This is useful, but it should not be required
  in the default PR gate until the runtime and dependency cost are justified.

## Local E2E Smoke Contract

The local-e2e smoke test should run from an installed package or editable
install, not by directly importing internals. It should:

- prepare a fixture repository with a committed base file;
- write a small fake local agent script that edits the fixture and optionally
  writes JSON telemetry;
- create a temporary `context-eval.yaml` and `tasks.yaml`;
- invoke `context-eval run --config <path> --cleanup-policy successful`;
- invoke `context-eval report <run-dir>`;
- invoke `context-eval export <run-dir> --format csv --output summary.csv`;
- invoke `context-eval export <run-dir> --format json --output summary.json`;
- invoke `context-eval ui --config <path> --run-dir <run-dir> --output
  context-eval-ui.html`;
- assert these artifacts exist and are parseable: `results.jsonl`,
  `run_manifest.json`, `report.md`, `summary.csv`, `summary.json`, and
  `context-eval-ui.html`;
- assert generated outputs keep the local observation framing and do not include
  network calls such as `fetch(`, `XMLHttpRequest`, `WebSocket`, `http://`, or
  `https://`.

The smoke should stay short enough for PR CI. It should use one task, one or two
variants, and one fake local agent so the test validates orchestration rather
than trying to benchmark an agent.

## CI Contract

CI should keep the existing pytest matrix, ruff check, example config
validation, skill validation, and package build jobs.

The first implementation uses a separate `local-e2e` job after package
installation. The smoke runs on one Python version and one OS. It is marked with
the `local_e2e` pytest marker and excluded from the default pytest matrix, so
routine unit and integration tests do not silently absorb the higher-level
workflow cost. CI runs the smoke with:

```bash
python -m pytest tests/test_local_e2e_smoke.py -m local_e2e
```

If the smoke becomes slower or flaky, keep the separate job boundary and fix the
fixture or orchestration issue rather than weakening the smoke. The job name
should make clear that it is local-e2e, not only unit tests.

## Non-Goals

- This is not a benchmark or leaderboard.
- The smoke must not call network services.
- The smoke must not call hosted services.
- The smoke must not install or run a real external agent.
- The smoke should use no hosted services and no real external coding agent.
- It must not depend on provider credentials.
- It must not add an LLM judge.
- The smoke must not require browser automation in the default PR gate.
- A Playwright browser smoke is an optional follow-up for UI-heavy changes, not
  a required first implementation.

## Acceptance Criteria

- `docs/development-plan.md` lists the local-e2e CI smoke as a capability epic
  before later feature work.
- Tests define the local-e2e smoke contract before implementation.
- CI has a clearly named local-e2e check through the separate `local-e2e` job
  and the `local_e2e` pytest marker.
- The smoke runs only against local artifacts and fixture repositories.
- The smoke verifies `context-eval run`, `report`, `export`, and `ui` through
  the installed CLI.
- Missing telemetry remains empty or null and is never guessed.
