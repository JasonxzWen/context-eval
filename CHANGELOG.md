# Changelog

## Unreleased

- Add a project documentation site entry, demo workflow, architecture overview,
  evaluation methodology, artifact model, FAQ, and GitHub Pages setup notes.

## v0.1.2 - 2026-05-14

- Add a Windows portable local app package builder that bundles the release
  wheel, dependency wheelhouse, frontend `dist`, and a double-click launcher for
  users who should not create a venv or run `pip` manually.
- Add `context-eval-app --frontend-dist` so packaged launchers can serve
  bundled frontend assets outside the Python wheel.
- Archive the Windows portable launcher OpenSpec requirements into the main
  specs after implementation and CI validation.

## v0.1.1 - 2026-05-13

- Add named agent profiles, noninteractive agent x task x variant x trial
  matrix planning, and a fixture-backed agent-matrix example for Codex CLI,
  Claude Code, traecli, and custom local commands.
- Add optional agent executable checks for `validate-config --check-agents`
  and a profile-map local-e2e smoke using the fixture repository.
- Add the frontend tooling foundation, API-backed loopback local app workflow,
  and Chinese-first config/tasks editing path with safe save/reload behavior.
- Add the packaged local app launcher entry point, startup diagnostics, and
  local launcher log path for the no-command-line app startup path.
- Add installed package smoke coverage for the `context-eval-app` launcher
  startup preflight without opening a browser or crossing the manual publish
  checkpoint.
- Archive completed OpenSpec changes into main specs for agent profiles,
  frontend tooling, local app workflow, and launcher install smoke.

## v0.1.0 - 2026-05-12

- Add the initial SDD/TDD development roadmap.
- Add runner correctness improvements, strict validation, task filters, fixture
  examples, dry-run previews, init, trials, inspect/compare commands, and a
  local static UI generator.
- Modernize package metadata to use SPDX license metadata instead of
  table-form license metadata.
- Document Python and platform support expectations for release readiness.
- Add automated package artifact inspection for wheel and sdist release checks.
- Add a release-state check for hidden local release blockers.
- Add development plan status reconciliation and an active backlog handoff that
  names validation command timeout defaults as the next planned work.
- Add validation command timeout defaults with `evaluation.timeout_seconds` and
  `task.validation.timeout_seconds`.
- Replan the development roadmap around larger capability PRs and replace the fine-grained active backlog with capability epics.
- Clarify that Ralph stories remain SDD/TDD units inside a capability PR.
- Add a release preparation entrypoint with a manual tag and publish checkpoint.
- Specify a local-e2e CI smoke and test taxonomy as the next pre-feature
  capability gate.
- Add a release candidate install smoke that installs from built package artifacts
  and runs the local fixture workflow before the manual publish
  checkpoint.
- Add specs and a development plan for agent profiles, noninteractive
  multi-agent matrices, local app/server mode, full Web UI workflows, and a
  no-command-line launcher path.
