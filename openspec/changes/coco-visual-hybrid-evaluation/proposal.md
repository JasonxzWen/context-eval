## Why

Users can already run local coding-agent evaluations, but the local app does not
yet let them author a complete Coco-focused workflow with explicit expected
outcomes and evaluation criteria. This change makes the next product slice a
visual, local-first authoring and review workflow that keeps deterministic hard
checks as the correctness anchor.

## What Changes

- Add `coco-visual-hybrid-evaluation` as the next active capability.
- Add Coco as a first-class local agent profile kind while preserving existing
  `agent` and `agents` config compatibility.
- Extend task YAML with optional `expected_outcome`, `hard_evaluation`, and
  `soft_evaluation` sections.
- Generate deterministic per-case hard evaluation artifacts from local patches,
  touched paths, validation results, retained workspaces, and task criteria.
- Generate optional soft evaluation payload artifacts for later human or local
  judge review without calling hosted model APIs.
- Surface hard/soft evaluation summaries in local app planning, results,
  Markdown report, exports, and the React local app workflow.
- Add a minimal Coco-focused example using fake/local execution for tests.

## Capabilities

### New Capabilities

- `coco-visual-hybrid-evaluation`: Coco-first visual authoring, expected
  outcome modeling, deterministic hard checks, optional soft payload generation,
  local app review, and artifact/report/export integration.

### Modified Capabilities

- `agent-profiles`: Accept `kind: "coco"` as a first-class local profile kind
  and keep executable preflight side-effect-free.
- `local-app-workflow`: Add structured expected outcome, hard evaluation, soft
  payload, run planning, execution, and result review requirements to the local
  app workflow.

## Impact

- Runtime models: `context_eval/models.py`
- Config validation and local app path safety: `context_eval/config.py`,
  `context_eval/config_editor.py`, `context_eval/local_app.py`
- Runner artifacts: `context_eval/runner.py` plus new local evaluation helpers
- Reports and exports: `context_eval/reporting.py`,
  `context_eval/reports/markdown.py`, report template, and `context_eval/export.py`
- Frontend workflow: `frontend/src/App.tsx`, styles, fixtures, and tests
- Docs, examples, and OpenSpec artifacts
