# Harness Hub Import

This repository vendors the development capability library from:

- Source: `https://github.com/JasonxzWen/harness-hub`
- Former source name: `JasonxzWen/skill-hub`
- Initial imported commit: `65523f9211a1bf8adaf9247f3dfbc14484251f1e`
- Latest refreshed commit: `586950abb086828bca7361ec3f17c5397bdd05c3`
- Import date: `2026-05-08`
- Latest refresh date: `2026-06-02`
- Minimal harness install date: `2026-06-03`
- Minimal harness package: `@jasonwen/harness-hub@0.1.11`

Imported capability roots:

- `.agents/skills/`
- `.codex/skills/`
- `.codex/agents/`
- `.harness-hub/lock.json`
- `skills/`
- `openspec/`
- `scripts/`
- root minimal harness files:
  - `AGENTS.md`
  - `clean-state-checklist.md`
  - `definition-of-done.md`
  - `feature_list.json`
  - `progress.md`
  - `session-handoff.md`
  - `tasks/current-task.md`

The upstream repository's `README.md` file is intentionally not imported. The
root `AGENTS.md` now comes from the Harness Hub minimal target bootstrap and is
tracked as this repository's concise Codex operating contract.

The imported assets are used as project-local development support: skill
definitions, focused agent role configs, OpenSpec helpers, workflow scripts,
and validation utilities. They are not part of the `context_eval` runtime
package unless explicitly referenced by future packaging changes.

The `2026-05-25` refresh migrates the current upstream `skills/` set into
`.codex/skills/`. Same-name skills in `.codex/skills/` were overwritten, and
duplicates that had lived under `.agents/skills/` were removed so each skill has
one project-local home.

The `2026-06-02` refresh syncs the current Harness Hub standard `skills/` set
into `.codex/skills/` while preserving context-eval's host-local
`agents/openai.yaml` metadata. It updates the workflow router,
`hub-maintenance-workflow`, delivery closeout, and related helper scripts to the
Harness Hub vocabulary.

The migrated set includes the earlier low-noise workflow skills:

- `html-work-reports`: self-contained HTML work handoffs with templates,
  source-linked evidence, generator, and validator assets.
- `compound-code-review`: deep pre-PR review with structured findings and
  reviewer lenses.
- `diagnose`: reproducible bug and performance-regression diagnosis loops.
- `prototype`: clearly marked throwaway prototypes for one design question.
- `grill-me`: one-question-at-a-time plan pressure testing.

It also includes newer upstream skills such as `effective-interact`,
`feynman-learning-coach`, `workflow-router`, and `claude-api`. The Harness Hub
refresh adds `clone-website`, `design-taste-frontend`,
`karpathy-guidelines`, `source-to-insight-blog`, and `stop-slop`.

The `2026-06-03` update runs the Harness Hub standard minimal bootstrap and
records lock-backed ownership in `.harness-hub/lock.json`. It installs the
root continuity files, `scripts/harness-validate.mjs`, and the standard
`skills/` tree. The lock currently records 43 managed components:
`harness:minimal` plus 42 standard skills. `harness-hub update --dry-run`
reports no pending updates or blockers for those managed components.

The update still does not import Harness Hub npm CLI lifecycle source code,
`.claude-plugin/`, `site/`, or upstream top-level reports because those are
source-repo tooling, host packaging, or generated artifacts, not context-eval
runtime package inputs. `.harness-hub/reports/` is ignored so generated install
reports remain local. `harness:website-cloner` is visible in the upstream
component list, but it is an explicit smoke scaffold outside the standard
minimal target and is not managed by this lock.

Most upstream Harness Hub documentation was intentionally removed from this
repository because it describes general skill-pack research, source-project
analysis, npm lifecycle setup, and local target bootstrap workflows that are not
specific to context-eval. This file is the retained provenance record.

The optional Codex configuration is tracked as `.codex/config.example.toml`.
Maintainers can copy it to `.codex/config.toml` locally when they want to opt in
to the project-local `.codex/skills/` and agent roles. The active
`.codex/config.toml` path is ignored so ordinary clones do not silently enable
external tooling.

Harness Hub minimal state is validated with `node scripts\harness-validate.mjs`
and `npx -y @jasonwen/harness-hub@latest validate-harness . --json`. The
legacy project-local `.codex/skills/` tree is still validated with
`powershell -ExecutionPolicy Bypass -File scripts\validate-skills.ps1 -SkipExternal`.
