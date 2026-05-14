# Local App Harness Readiness Reference

This note records the selective Skill Hub reference used for the Chinese local
app configuration editor phase.

- Source: `https://github.com/JasonxzWen/skill-hub`
- Inspected commit: `42c3065378e1d1d2851ca0e387e915a2841b885e`
- Use: reference for local app readiness; maintainer-only skill refresh for
  development workflows, with no `context_eval` runtime package import.

## Borrowed Patterns

Skill Hub keeps its routine gates explicit:

- `build`: produce the distributable entrypoint before release checks.
- `test`: run the repository's fixture-backed automated tests.
- `validate`: compose typecheck, tests, and skill validation into one local
  gate.
- `validate:release`: add build, CLI smoke, and package dry-run checks.

Its `html-work-reports` skill also adds a useful reporting discipline for
maintainer handoffs:

- conclusion-first, self-contained static HTML reports;
- pre-rendered Markdown, Mermaid, code snippets, and diffs for primary content;
- source-linked file evidence and verification status blocks;
- validation that can report degraded browser coverage instead of claiming a
  false pass.

For context-eval, the equivalent gate matrix is:

| Area | Gate | Purpose |
| --- | --- | --- |
| Python runtime | `.\.venv\Scripts\python.exe -m pytest --basetemp C:\tmp\context-eval-pytest` | API, runner, config, reporting, and docs contracts |
| Frontend | `python scripts\validate-frontend.py --install --install-browsers` | typecheck, Vitest, build, and Playwright desktop/narrow acceptance |
| Lint | `.\.venv\Scripts\python.exe -m ruff check .` | Python style and import hygiene |
| Spec | `openspec validate --all --no-interactive` | active and archived OpenSpec consistency |
| Diff | `git diff --check` | whitespace and patch hygiene |

## Readiness Shape

Skill Hub's agent-readiness analysis is useful because it stays read-only,
category-based, evidence-backed, and scoreless. The local app should use the
same shape when deciding whether the harness is ready for broader automation:

- context budget: instructions and always-loaded files are bounded;
- outcomes: OpenSpec tasks, docs, and acceptance criteria are explicit;
- verification: build, test, lint, frontend, browser, spec, and diff gates are
  named;
- routing: fake/local agents are used before real external-agent smoke;
- automation candidates: recurring or multi-agent work remains manual until
  checkable gates exist;
- learning capture: docs and tests record the behavior instead of relying on
  chat history.

This repository should keep readiness as a document/test entry for now. It
should not add a scoring model, hosted dashboard, remote database, external
agent installer, or automatic target-repository commit workflow.

The HTML report skill is maintainer tooling only. It can improve review,
handoff, and architecture-explainer artifacts, but it must not replace the
existing `context-eval ui` static export or add JavaScript build requirements to
the Python runtime package.
