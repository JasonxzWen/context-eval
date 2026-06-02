# Local App Harness Readiness Reference

This note records the selective Harness Hub reference used for the Chinese
local app configuration editor phase.

- Source: `https://github.com/JasonxzWen/harness-hub`
- Former source name: `JasonxzWen/skill-hub`
- Inspected commit: `586950abb086828bca7361ec3f17c5397bdd05c3`
- Use: reference for local app readiness; maintainer-only skill refresh for
  development workflows, with no `context_eval` runtime package import.

## Borrowed Patterns

Harness Hub keeps its routine gates explicit:

- `build`: produce the distributable entrypoint before release checks.
- `test`: run the repository's fixture-backed automated tests.
- `validate`: compose typecheck, tests, and skill validation into one local
  gate.
- `validate:release`: add build, CLI smoke, and package dry-run checks.
- `validate-harness`: inspect a target repo's root harness files, QA boundary,
  skill trigger hygiene, verification-command detection, and lifecycle state
  without mutating files.

Its current `effective-interact` and delivery workflow skills add a useful
reporting discipline for maintainer handoffs:

- conclusion-first, self-contained static HTML reports;
- pre-rendered Markdown, Mermaid, code snippets, and diffs for primary content;
- source-linked file evidence and verification status blocks;
- validation that can report degraded browser coverage instead of claiming a
  false pass;
- PR closeout that checks mergeability, CI/check runs, conflicts, and branch
  protection blockers after a pushed PR branch settles.

For context-eval, the equivalent gate matrix is:

| Area | Gate | Purpose |
| --- | --- | --- |
| Python runtime | `.\.venv\Scripts\python.exe -m pytest --basetemp C:\tmp\context-eval-pytest` | API, runner, config, reporting, and docs contracts |
| Frontend | `python scripts\validate-frontend.py --install --install-browsers` | typecheck, Vitest, build, and Playwright desktop/narrow acceptance |
| Lint | `.\.venv\Scripts\python.exe -m ruff check .` | Python style and import hygiene |
| Spec | `openspec validate --all --no-interactive` | active and archived OpenSpec consistency |
| Diff | `git diff --check` | whitespace and patch hygiene |
| Skill library | `powershell -ExecutionPolicy Bypass -File scripts\validate-skills.ps1 -SkipExternal` | local Codex/worktree skill availability and host metadata |

Codex local mode uses the tracked `.codex/skills/` tree plus optional
`.codex/config.example.toml`. A fresh git worktree gets the same tracked skill
tree without a machine-specific setup command. Worktree smoke should confirm:

- `.codex\skills\workflow-router\SKILL.md` exists;
- newer Harness Hub skills such as `clone-website`, `design-taste-frontend`,
  `karpathy-guidelines`, `source-to-insight-blog`, and `stop-slop` exist;
- each skill has `agents\openai.yaml` for local Codex activation metadata;
- `scripts\validate-skills.ps1 -SkipExternal` passes from the worktree root.

## Readiness Shape

Harness Hub's agent-readiness analysis is useful because it stays read-only,
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

Harness Hub root harness initialization is source reference only in
context-eval. This repository should not run `init-harness` against itself as a
default setup step, should not add upstream `.harness-hub/state` files, and
should not install Harness Hub assets into users' target repositories through
the context-eval runtime.

The HTML and rich-interaction report skills are maintainer tooling only. They
can improve review, handoff, and architecture-explainer artifacts, but they must
not replace the existing `context-eval ui` static export or add JavaScript build
requirements to the Python runtime package.
