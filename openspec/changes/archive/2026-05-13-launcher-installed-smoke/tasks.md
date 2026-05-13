## 1. Contract Tests And Docs

- [x] 1.1 Add failing tests for launcher `--check-startup` CLI behavior and log output.
- [x] 1.2 Add failing tests for install-smoke dry-run and real command planning to include `context-eval-app`.
- [x] 1.3 Update README, release checklist, local app workflow, release smoke spec, and changelog with launcher install-smoke acceptance.

## 2. Launcher Startup Preflight

- [x] 2.1 Implement a non-serving `context-eval-app --check-startup` mode that validates launcher inputs, writes a local diagnostic, prints the log path, and exits.
- [x] 2.2 Preserve existing launcher behavior for normal startup, browser handoff, and startup failure diagnostics.

## 3. Release Install Smoke

- [x] 3.1 Resolve the installed `context-eval-app` script in the temporary environment.
- [x] 3.2 Run the launcher startup preflight from `scripts/install-smoke-artifacts.py` with `--no-browser`, `--port 0`, and the generated local config.
- [x] 3.3 Keep the release smoke local-only and stopped before tag/publish operations.

## 4. Verification

- [x] 4.1 Run targeted pytest coverage for launcher and install-smoke behavior.
- [x] 4.2 Run full repo verification gates requested for this change.
- [x] 4.3 Clean regenerated frontend and local smoke artifacts.
