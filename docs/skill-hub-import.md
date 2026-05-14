# Skill Hub Import

This repository vendors the development capability library from:

- Source: `https://github.com/JasonxzWen/skill-hub`
- Initial imported commit: `65523f9211a1bf8adaf9247f3dfbc14484251f1e`
- Latest refreshed commit: `42c3065378e1d1d2851ca0e387e915a2841b885e`
- Import date: `2026-05-08`
- Latest refresh date: `2026-05-14`

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
definitions, focused agent role configs, OpenSpec helpers, Ralph loop scripts,
and validation utilities. They are not part of the `context_eval` runtime
package unless explicitly referenced by future packaging changes.

The `2026-05-14` refresh imports the upstream low-noise minimal profile skills
that were not present in the original snapshot:

- `html-work-reports`: self-contained HTML work handoffs with templates,
  source-linked evidence, generator, and validator assets.
- `compound-code-review`: deep pre-PR review with structured findings and
  reviewer lenses.
- `diagnose`: reproducible bug and performance-regression diagnosis loops.
- `prototype`: clearly marked throwaway prototypes for one design question.
- `grill-me`: one-question-at-a-time plan pressure testing.

The refresh intentionally does not import `feynman-learning-coach`, the harness
template profile, Skill Hub CLI lifecycle code, or the upstream top-level
`reports/` showcase. Those are either learning/session-specific, target-repo
installation surfaces, or not needed for this project's runtime package.

Most upstream skill-hub documentation was intentionally removed from this
repository because it describes general skill-pack research, source-project
analysis, and local setup workflows that are not specific to context-eval. This
file is the retained provenance record.

The optional Codex configuration is tracked as `.codex/config.example.toml`.
Maintainers can copy it to `.codex/config.toml` locally when they want to opt in
to the project-local skills and agent roles. The active `.codex/config.toml`
path is ignored so ordinary clones do not silently enable external tooling.
