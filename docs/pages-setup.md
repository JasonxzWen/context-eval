# GitHub Pages Setup

[Back to documentation index](index.md).

This repository is prepared for a lightweight documentation site from the
`docs/` directory. The site entry is `docs/index.md`.

No GitHub Pages deployment workflow is added by default. The intended first
setup path is GitHub's built-in Pages source configuration for a project site.

## Maintainer Setup

1. Open the repository settings in GitHub.
2. Go to Pages.
3. Set the source to deploy from a branch.
4. Select the default branch and the `/docs` folder.
5. Save the setting and wait for GitHub Pages to publish the site.

The site uses Markdown files and a lightweight `docs/_config.yml`. It does not
add a Node, Vite, or external CDN path. The existing `frontend/` package remains
for the loopback local app, not for the public project documentation site.

## What The Site Is For

The Pages site is a public documentation entry for the project: product
positioning, the deterministic demo workflow, architecture, evaluation
methodology, artifact model, FAQ, and maintainer setup notes.

## What The Site Is Not For

The Pages site is not the context-eval runtime, not a hosted dashboard, not a
shared report server, and not a place to publish generated run artifacts. It
should not expose `.context-eval/` outputs, target repository patches,
validation logs, retained workspaces, or local app frontend build output.

The local app remains local because it can save selected local files, run
preflight checks, start local evaluations, stream logs, and inspect run
artifacts. Those actions belong on the user's machine behind an explicit
loopback launch, not on a public GitHub Pages site.

## Site Entry Points

- `docs/index.md`: public landing page for the documentation site.
- `docs/demo-workflow.md`: deterministic fixture-backed onboarding path.
- `docs/architecture.md`: runtime flow and mode boundaries.
- `docs/evaluation-methodology.md`: comparison and confidence model.
- `docs/artifact-model.md`: local artifact reference.
- `docs/faq.md`: scope and behavior questions.

## Boundaries

The project site should keep the same product framing as the README:

- context-eval is local-first;
- it compares context variants under controlled local conditions;
- validation commands and human review remain necessary;
- outputs are local observations, not absolute model rankings;
- static UI is offline and export-only;
- local app mode is an explicit loopback local mode.

If maintainers later add a GitHub Pages workflow, keep it docs-only, trigger it
only on relevant documentation/site changes where practical, use standard
GitHub Pages deployment actions, and do not publish local app frontend assets as
the project documentation site.
