## ADDED Requirements

### Requirement: Launcher startup preflight

The installed local app launcher SHALL provide a startup preflight mode that
validates launcher inputs and exits without serving the local app or opening a
browser.

#### Scenario: Preflight validates local launcher inputs

- **WHEN** a user runs `context-eval-app` with a workspace, config path,
  `--no-browser`, `--port 0`, and the startup preflight option
- **THEN** the launcher validates the workspace, config path, loopback startup
  settings, frontend availability, and local launcher log path
- **AND** the command exits successfully without opening a browser or blocking
  in the server loop

#### Scenario: Preflight reports local diagnostics

- **WHEN** startup preflight succeeds
- **THEN** the launcher writes a local diagnostic line to the workspace launcher
  log and prints the launcher log path for the user

#### Scenario: Preflight preserves local-only boundaries

- **WHEN** startup preflight runs
- **THEN** it does not run agent commands, run validation commands, install
  dependencies, create commits, create tags, publish packages, or call hosted
  services

### Requirement: Installed launcher release smoke

The release candidate install smoke SHALL verify the installed `context-eval-app`
entry point in addition to the installed `context-eval` CLI.

#### Scenario: Dry run describes launcher smoke coverage

- **WHEN** the install smoke runs in dry-run mode
- **THEN** the printed plan includes the installed `context-eval-app` launcher
  startup preflight command
- **AND** the plan keeps the manual publish checkpoint outside the smoke

#### Scenario: Installed smoke runs launcher preflight

- **WHEN** the install smoke runs against built package artifacts
- **THEN** it invokes the installed `context-eval-app` console script with the
  local temporary workspace, config, `--no-browser`, `--port 0`, and the startup
  preflight option
- **AND** it continues to use only local fixture inputs and generated local
  artifacts
