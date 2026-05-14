## 1. Contracts And Specs

- [x] 1.1 Add OpenSpec proposal, design, spec, and task artifacts for the Windows portable launcher.
- [x] 1.2 Add failing tests for portable zip contents, startup script behavior, and docs.
- [x] 1.3 Add failing tests for `context-eval-app --frontend-dist` option wiring.

## 2. Packaging Implementation

- [x] 2.1 Implement `scripts/build-windows-portable.py` to assemble the portable archive from a built wheel and frontend `dist`.
- [x] 2.2 Generate `Start Context Eval.cmd`, `scripts/start-context-eval.ps1`, and package README content.
- [x] 2.3 Support dependency wheelhouse download for release builds and a no-download mode for deterministic tests.

## 3. Launcher And Docs

- [x] 3.1 Add `--frontend-dist` to `context-eval-app` and preserve existing launcher defaults.
- [x] 3.2 Document the portable zip build command and one-click startup flow in README, local app workflow, and release checklist.
- [x] 3.3 Keep no-CLI packaging boundaries explicit: no hosted service, no coding-agent installation, no auto tags or publishing.

## 4. Verification

- [x] 4.1 Run targeted tests for the portable builder and launcher option.
- [x] 4.2 Run full Python, frontend, OpenSpec, Ruff, and diff checks.
- [x] 4.3 Clean regenerated local artifacts.
