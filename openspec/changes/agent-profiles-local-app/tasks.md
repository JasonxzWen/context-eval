## 1. Agent Profiles

- [x] 1.1 Update `docs/agent-profiles.md`, `docs/adapter-api.md`, and `docs/configuration.md` with the accepted profile schema and compatibility rules.
- [x] 1.2 Add model tests for single `agent` compatibility, `agents` validation, mixed-shape rejection, supported profile kinds, and command template variables.
- [x] 1.3 Implement profile parsing and rendered command preview helpers in `context_eval/models.py` and adapter-facing modules.
- [x] 1.4 Expand runner planning to selected agent x task x variant x trial while preserving deterministic manifest and result row ordering.
- [x] 1.5 Update report, export, compare, inspect, and static UI tests for multi-agent artifact semantics.
- [x] 1.6 Add optional agent executable preflight and fixture-backed profile-map smoke coverage without implementing local app/server mode.

## 2. Local App Server

- [x] 2.1 Update `docs/local-app-workflow.md` with the final endpoint list and safety model before implementation starts.
- [x] 2.2 Add API contract tests for config save/load, side-effect-free preflight, run planning, run lifecycle, log streaming, and artifact reads.
- [x] 2.3 Implement an explicit local app command that binds to loopback by default and reuses existing config, runner, and reporting modules.
- [x] 2.4 Add path-safety checks for local config writes, output directories, and artifact reads.
- [x] 2.5 Add local-e2e coverage using the fixture repository and fake local agent.

## 3. Full Web UI

- [x] 3.1 Design the first-run, configuration, evaluation criteria, preflight, run, and results views around non-technical user workflows.
- [x] 3.2 Implement UI controls for repo setup, tasks, variants, overlays, agent profiles, trials, jobs, cleanup policy, and validation commands.
- [x] 3.3 Implement run monitoring, stop controls, log tails, risk signals, patch links, and exports.
- [x] 3.4 Verify the UI with browser automation across desktop and narrow viewports.
- [x] 3.5 Update README and screenshots or generated examples after the workflow is stable.

## 4. No-CLI Packaging

- [x] 4.1 Decide the launcher packaging approach after local app mode is stable: use the installed `context-eval-app` script as the shortcut target for future OS packaging.
- [x] 4.2 Add launcher startup checks and diagnostics for workspace/config paths, loopback startup, browser handoff, and local log location.
- [x] 4.3 Document packaged installation/startup/recovery for non-technical users.
- [x] 4.4 Keep package release automation stopped at the existing manual tag and publish boundary.

## 5. Chinese Web Config Editor And Harness Readiness

- [x] 5.1 Update the local app spec and docs for Chinese UI copy, config/tasks load-save-reload, safe YAML editing, and local-only write boundaries.
- [x] 5.2 Add API tests for config/tasks round-trip reload, unknown-field preservation, and config/tasks/output/overlay path safety.
- [x] 5.3 Add frontend unit tests for Chinese labels, save-and-reload status, task YAML editing, and API-only workflow calls.
- [x] 5.4 Add Playwright coverage for load, edit, save, reload, preflight, plan, run, results, and exports across desktop and narrow viewports.
- [x] 5.5 Implement the Chinese API-backed config/tasks editor and lightweight motion with `prefers-reduced-motion` support.
- [x] 5.6 Add a minimal Skill Hub reference analysis for build/test/validate gates, acceptance matrix, and readiness boundaries.
- [x] 5.7 Run the full requested verification gates and remove regenerated local artifacts.
