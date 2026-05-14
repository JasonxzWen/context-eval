# context-eval Project Documentation

context-eval is a local-first Context A/B Testing Framework for coding agents.
It compares context variants under controlled local conditions and records the
resulting artifacts for engineering review.

Use these docs when you want to understand the product boundary, run the fixture
demo, inspect the architecture, or prepare the repository documentation site.

## Why Context A/B Testing Exists

Agent-facing context changes are easy to ship and hard to evaluate. A new
`AGENTS.md`, local documentation bundle, DeepWiki export, skill, or rule set can
look useful while still making real coding-agent tasks slower, less stable, or
less correct.

context-eval keeps that question local and inspectable: hold the repository,
task, command template, trials, and validation commands steady, then change the
context variant and review the recorded artifacts.

## Minimal Local Workflow

1. Install context-eval in editable mode.
2. Initialize or choose an evaluation workspace.
3. Define local tasks, context variants, agent command templates, and validation
   commands.
4. Run config validation and a dry-run matrix preview.
5. Run a small local evaluation.
6. Inspect `report.md`, `results.jsonl`, `run_manifest.json`, logs, patches,
   exports, and optional UI output before drawing conclusions.

## Start Here

- [README quickstart](https://github.com/JasonxzWen/context-eval#quickstart)
  covers installation, starter config, runs, reports, exports, and UI commands.
- [Demo workflow](demo-workflow.md) uses the bundled fixture repository and fake
  local agent. It does not require hosted services, provider credentials, or
  real external coding agents.
- [Architecture](architecture.md) explains the run flow, runtime package
  boundary, static UI mode, local app mode, and artifact-only reporting model.
- [Evaluation methodology](evaluation-methodology.md) explains what is being
  evaluated and how confidence should be interpreted.
- [Artifact model](artifact-model.md) describes the local files produced by a
  run and how they support reproducibility, debugging, review, and exports.
- [FAQ](faq.md) answers the most common boundary and workflow questions.
- [Local app workflow](local-app-workflow.md) documents the explicit loopback
  local app mode.
- [Agent profiles](agent-profiles.md) documents named local command profiles.
- [Frontend workflow](frontend-workflow.md) documents the local app frontend
  build, test, and browser acceptance gate.
- [Development plan](development-plan.md) tracks the staged capability roadmap
  and release/development boundaries.
- [Release checklist](release-checklist.md) documents release preparation and
  manual publish boundaries.

## Documentation Map

Read the docs in this order for a first pass:

1. [Demo workflow](demo-workflow.md) to see the smallest deterministic path.
2. [Evaluation methodology](evaluation-methodology.md) to understand the
   comparison model.
3. [Architecture](architecture.md) to understand how runs are planned and
   recorded.
4. [Artifact model](artifact-model.md) to inspect outputs from a completed run.
5. [FAQ](faq.md) to check scope, non-goals, and mode boundaries.

Maintainers preparing a GitHub Pages project site should also read
[Pages setup](pages-setup.md).

## Project Boundaries

context-eval is local-first. It compares context variants such as `AGENTS.md`,
local docs, DeepWiki exports, skills, and rules against explicit local tasks and
validation commands.

The outputs are local observations, not absolute model rankings. The
validation confidence boundary comes from project validation commands and human
review, not from patch size or an LLM judge alone. Reporting is artifact-only:
completed reports, exports, terminal summaries, and the static UI read recorded
local artifacts.

context-eval is not a leaderboard, hosted service, provider billing tool,
credential manager, automatic agent installer, or automatic target-repository
commit workflow. The static UI is offline and export-only. The local app is an
explicit loopback mode that runs on the user's machine.
