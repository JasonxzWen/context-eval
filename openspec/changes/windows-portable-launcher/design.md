## Context

`context-eval-app` exists as a Python console script and `v0.1.1` verifies that
the installed launcher can run a startup preflight. That still leaves too much
setup for non-technical users: they must have a Python command ready, create a
venv, install the wheel, and invoke the launcher manually. The accepted next
step is a Windows portable zip that still requires local Python 3.11+, but
automates environment creation, package installation, and app startup.

## Goals / Non-Goals

**Goals:**

- Build a release artifact shaped as `context-eval-windows-x64-<version>.zip`.
- Include the app wheel, dependency wheels, frontend `dist`, and a double-click
  startup wrapper.
- Keep the extracted package self-contained after unzip, except for requiring
  Python 3.11+ to be installed on the machine.
- Start the existing loopback local app and browser without requiring users to
  type `context-eval` commands.

**Non-Goals:**

- Do not build a PyInstaller executable in this change.
- Do not add MSI/Setup.exe, Start Menu registration, auto-update, code signing,
  or uninstall behavior.
- Do not install Codex, Claude Code, traecli, coco, target repository
  dependencies, or any real coding agent.
- Do not change the local-only artifact and non-leaderboard boundaries.

## Decisions

- Use a portable zip first. It is simpler to validate than a bundled executable
  and matches the current Python package architecture.
- Bundle a wheelhouse and install with `pip --no-index --find-links` so users do
  not need to run pip manually and repeated startup does not depend on hosted
  package resolution.
- Keep frontend assets outside the Python wheel and pass them explicitly through
  a new `context-eval-app --frontend-dist` option. This avoids expanding the
  runtime package scope while still letting portable launches serve the UI.
- The startup script creates a package-local `.venv` and `workspace/`. This
  keeps app state close to the extracted package and avoids modifying user
  Python environments.

## Risks / Trade-offs

- The package still requires Python 3.11+. Mitigation: startup script checks
  `py -3.13`, `py -3.12`, `py -3.11`, and `python`, then prints an actionable
  error if none work.
- Bundling dependency wheels makes the zip larger. Mitigation: this is the
  first no-CLI path; size is acceptable in exchange for a repeatable startup.
- Windows script behavior is platform-specific. Mitigation: tests inspect the
  generated archive and scripts, and manual release acceptance can run the
  double-click path on Windows.
