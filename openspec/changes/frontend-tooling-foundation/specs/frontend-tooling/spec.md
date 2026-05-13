## ADDED Requirements

### Requirement: Frontend package quality gate

The system SHALL provide a development-only frontend package with deterministic
typecheck, unit/component test, build, browser acceptance, and combined
validation commands for the planned local app UI.

#### Scenario: Frontend validation runs all local app UI gates

- **WHEN** a maintainer runs the documented frontend validation command
- **THEN** the command runs TypeScript checks, unit/component tests, production
  build, and browser acceptance in a deterministic order

#### Scenario: Existing Python CLI users do not need Node at runtime

- **WHEN** a user runs existing context-eval CLI, runner, report, export, or
  static UI commands without working on the local app frontend
- **THEN** those commands do not require Node or npm to be installed

### Requirement: Browser acceptance foundation

The system SHALL include a browser acceptance harness for frontend changes
before the full local app server and Web UI workflow are implemented.

#### Scenario: Built frontend passes desktop and narrow smoke checks

- **WHEN** the browser acceptance command runs against the built frontend
- **THEN** it verifies the local app shell renders successfully in desktop and
  narrow browser viewports

#### Scenario: Acceptance uses deterministic local fixtures

- **WHEN** frontend acceptance tests need sample data before the local app API
  exists
- **THEN** they use deterministic local fixture data instead of hosted services,
  real coding agents, or remote network calls

### Requirement: Frontend build output contract

The system SHALL build frontend assets into a stable local output directory
that future local app server work can serve explicitly.

#### Scenario: Production build writes static assets

- **WHEN** the frontend build command completes successfully
- **THEN** static assets exist in the documented build output directory

#### Scenario: Runtime package scope remains unchanged

- **WHEN** this frontend foundation change is merged
- **THEN** Python package metadata does not add frontend build assets to the
  runtime package until a later local app server change consumes them

### Requirement: CI exposes frontend validation

The system SHALL expose the frontend quality gate as a clearly named CI job.

#### Scenario: Frontend validation is visible in CI

- **WHEN** CI runs for a pull request
- **THEN** a dedicated frontend validation job installs frontend dependencies
  and runs the combined frontend validation command

#### Scenario: Python and frontend gates remain separate

- **WHEN** CI runs Python tests, local-e2e smoke, skill validation, package
  build, and frontend validation
- **THEN** frontend failures are reported through the frontend job without
  weakening existing Python quality gates
