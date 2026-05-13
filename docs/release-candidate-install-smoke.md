# Release Candidate Install Smoke

This spec defines the release-candidate install smoke that runs after package
artifacts are built and inspected. It proves that a built local wheel can be
installed and used through the `context-eval` console script before a maintainer
creates tags or publishes packages.

The smoke is a release candidate gate, not a benchmark or leaderboard. It uses
only local inputs: the clean checkout or archive copy, built package artifacts, a
fixture repository, a fake local agent, temporary config files, and generated run
artifacts.

## Contract

The smoke must:

- select the built wheel from the release artifact directory;
- install that local wheel into a temporary Python environment;
- avoid dependency resolution from hosted services during the smoke step;
- run `context-eval validate-config` against a temporary local config;
- run `context-eval run` with one fixture task, one context variant, and a fake
  local agent;
- run `context-eval report`, `context-eval export` for CSV and JSON, and
  `context-eval ui`;
- run the installed `context-eval-app` launcher with
  `--no-browser --port 0 --check-startup` against the same temporary workspace
  and config;
- assert `results.jsonl`, `run_manifest.json`, `report.md`, `summary.csv`,
  `summary.json`, and `context-eval-ui.html` exist and are parseable;
- assert generated report, export, and UI artifacts do not contain hosted network call patterns such as `fetch(`, `XMLHttpRequest`, `WebSocket`,
  `http://`, or `https://`;
- stop at the manual publish checkpoint after the smoke succeeds.

## Non-Goals

- Do not create Git tags.
- Do not upload or publish packages.
- Do not call hosted services from the smoke.
- Do not install or run a real external coding agent.
- Do not add an LLM judge.
- Do not run against a live user repository.

## CI Contract

The package-build CI job should call the consolidated release preparation
entrypoint. That entrypoint builds artifacts, inspects them, runs this install
smoke, and then prints the manual publish checkpoint.

The smoke should install the project wheel from the local `dist` directory with
dependency installation disabled. CI may prepare runtime dependencies before the
release preparation command, but the smoke itself must use the built local wheel
and local fixture artifacts only. The launcher preflight is an installed entry
point acceptance check only; it must not open a browser, start an indefinite
server loop, install coding agents, or cross the manual publish checkpoint.
