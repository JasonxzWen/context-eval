# Harness Hub Import

This repository vendors the development capability library from:

- Source: `https://github.com/JasonxzWen/harness-hub`
- Former source name: `JasonxzWen/skill-hub`
- Initial imported commit: `65523f9211a1bf8adaf9247f3dfbc14484251f1e`
- Latest refreshed commit: `586950abb086828bca7361ec3f17c5397bdd05c3`
- Import date: `2026-05-08`
- Latest refresh date: `2026-06-02`

Imported capability roots:

- `.agents/skills/`
- `.codex/skills/`
- `.codex/agents/`
- `openspec/`
- `scripts/`

The upstream repository's `AGENTS.md` and `README.md` files were intentionally
not imported. Files named `AGENTS.md` or `README*` inside the imported roots
were also skipped to avoid changing this repository's agent instructions or
duplicating upstream project documentation.

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

The refresh still does not import Harness Hub npm CLI lifecycle code,
`harness/minimal` root harness files, `.claude-plugin/`, `site/`, or upstream
top-level reports because those are source-repo tooling, host packaging, or
target-repo bootstrap assets, not context-eval runtime package inputs.

Most upstream Harness Hub documentation was intentionally removed from this
repository because it describes general skill-pack research, source-project
analysis, npm lifecycle setup, and local target bootstrap workflows that are not
specific to context-eval. This file is the retained provenance record.

The optional Codex configuration is tracked as `.codex/config.example.toml`.
Maintainers can copy it to `.codex/config.toml` locally when they want to opt in
to the project-local skills and agent roles. The active `.codex/config.toml`
path is ignored so ordinary clones do not silently enable external tooling.

Codex local mode and git worktrees use the tracked `.codex/skills/` tree
directly. No machine-specific Harness Hub setup command is required for a fresh
context-eval worktree; skill availability is validated with
`powershell -ExecutionPolicy Bypass -File scripts\validate-skills.ps1 -SkipExternal`.
