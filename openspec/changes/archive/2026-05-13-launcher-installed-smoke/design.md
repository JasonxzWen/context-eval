## Context

PR #34 added the packaged `context-eval-app` entry point and launcher
diagnostics. The current release candidate install smoke installs the built
wheel and exercises the installed `context-eval` CLI through validate, run,
report, export, and static UI commands, but it does not prove that the new
launcher script is exposed by the installed package.

## Goals / Non-Goals

**Goals:**

- Add a deterministic launcher preflight command path that is safe in tests,
  release smoke runs, and CI.
- Exercise the installed `context-eval-app` console script from the existing
  release install smoke.
- Keep all smoke inputs local: built wheel, fixture repo, fake local agent,
  temporary config, generated artifacts, and launcher log.
- Document the new acceptance step without changing the manual tag/publish
  boundary.

**Non-Goals:**

- Do not add an OS installer, Start Menu integration, auto-update, or shortcut
  generation.
- Do not open a browser or run an indefinite server loop during the release
  smoke.
- Do not install or run real external coding agents.
- Do not publish packages, create tags, or upload artifacts automatically.

## Decisions

- Add a `--check-startup` option to `context-eval-app`. This reuses
  `build_launcher_startup` so config and path validation stay shared with real
  launch, then writes a preflight diagnostic and exits.
- Keep `--check-startup` in the launcher command rather than adding a separate
  maintainer-only script. The release smoke needs to prove the installed
  console entry point is usable, not just importable.
- Use `--no-browser --port 0 --check-startup` in the install smoke. `--port 0`
  keeps the acceptance command aligned with ephemeral local startup guidance,
  while `--check-startup` prevents the server loop from blocking.
- Extend existing release smoke tests instead of adding a new CI job. The
  launcher check is part of package install readiness and should remain in the
  consolidated `prepare-release.py` path.

## Risks / Trade-offs

- A preflight does not prove that a socket can bind. Mitigation: the real
  launcher path still has unit coverage for server bind handoff and failure
  diagnostics; this smoke focuses on installed entry point availability.
- The startup preflight creates a launcher log in a temporary workspace.
  Mitigation: this is a local artifact under the smoke work directory and is
  cleaned up with the temporary smoke workspace.
- Future OS-specific packaging may need separate manual verification.
  Mitigation: docs keep this as the first installed package smoke, not as a
  full OS installer acceptance test.
