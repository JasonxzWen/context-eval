## ADDED Requirements

### Requirement: Windows portable package

The release tooling SHALL be able to build a Windows portable package that
contains everything needed for one-click startup except a local Python 3.11 or
newer runtime.

#### Scenario: Portable zip contains startup assets

- **WHEN** the portable package builder runs with a built context-eval wheel and
  a built frontend asset directory
- **THEN** it creates a zip containing the app wheel, dependency wheelhouse,
  frontend `dist` files, a PowerShell startup script, a `.cmd` double-click
  wrapper, and a README

#### Scenario: Portable package installs from bundled wheels

- **WHEN** a user double-clicks the portable launcher
- **THEN** it creates or reuses a private venv inside the extracted package and
  installs context-eval from the bundled wheelhouse without requiring the user
  to run pip manually

### Requirement: One-click local app startup

The portable launcher SHALL start the local app from the extracted package
without requiring the user to type a context-eval CLI command.

#### Scenario: Launcher starts bundled frontend

- **WHEN** the startup script launches the app
- **THEN** it passes the bundled frontend `dist` directory to `context-eval-app`
  and starts the loopback local app with a package-local workspace

#### Scenario: Missing Python is actionable

- **WHEN** no Python 3.11 or newer runtime is available
- **THEN** the startup script prints an actionable error explaining that Python
  3.11 or newer is required and exits without creating partial app state

#### Scenario: Launcher preserves safety boundaries

- **WHEN** the portable launcher starts or fails
- **THEN** it does not install coding agents, install target repository
  dependencies, create commits, create tags, publish packages, or call hosted
  context-eval services
