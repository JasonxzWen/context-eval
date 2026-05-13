## 1. Contract Tests And Docs

- [x] 1.1 Add failing tests for the frontend tooling OpenSpec artifacts and development-plan placement.
- [x] 1.2 Add failing tests for frontend package scripts, root validation wrapper, CI job, and runtime package boundary.
- [x] 1.3 Document the frontend workflow in `docs/frontend-workflow.md` and link it from README/local app docs.

## 2. Frontend Package Foundation

- [x] 2.1 Create `frontend/` with Vite, React, TypeScript, Vitest, and Playwright configuration.
- [x] 2.2 Implement a minimal local app shell with deterministic fixture data and no local server dependency.
- [x] 2.3 Add unit/component tests for the app shell and fixture rendering.
- [x] 2.4 Add browser smoke tests for desktop and narrow viewports against the built frontend.

## 3. Validation And CI

- [x] 3.1 Add a root validation wrapper that installs/checks frontend dependencies and runs the combined frontend gate.
- [x] 3.2 Add a dedicated frontend validation CI job without weakening existing Python gates.
- [x] 3.3 Update development verification docs with the frontend validation command.

## 4. Verification

- [x] 4.1 Run targeted pytest tests for the new docs/tooling contracts.
- [x] 4.2 Run frontend validation.
- [x] 4.3 Run `openspec validate --all --no-interactive`.
- [x] 4.4 Run `git diff --check`.
