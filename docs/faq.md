# FAQ

[Back to documentation index](index.md).

## Is context-eval an agent benchmark?

No. context-eval records local observations for a selected repository, task
set, context variants, agent command or profile, validation commands, trials,
and machine state. It should not be presented as a global agent benchmark or
leaderboard.

## Why not use an LLM judge as the main correctness source?

The current scope keeps correctness grounded in project validation commands and
human engineering review. An LLM judge would add another model-dependent signal
that may not match the repository's tests, invariants, or acceptance criteria.

## How does context-eval keep comparisons fair?

It runs the same task, repo ref, agent command or selected profile, validation
commands, trials, and cleanup policy while changing the context variant overlay.
Each case gets an isolated workspace so variant files do not leak across cases.

## What happens when validation commands are missing?

The case is recorded with low confidence. Patches, logs, prompts, and diff stats
remain useful for review, but the result should not be treated as proof that the
task was solved.

## How should trials be interpreted?

Trials show repeated observations under the recorded local setup. They help
surface nondeterminism, flaky validation, and variant stability. They do not
create absolute claims about general agent capability.

## Can it compare multiple agents?

Yes, through named local agent profiles or aligned configs. Agent-level
summaries appear only when more than one `agent_name` is present. The summaries
remain local observations, not absolute rankings.

## Does it install Codex CLI, Claude Code, traecli, coco, or other agents?

No. context-eval can validate configured command executables when requested,
but it does not install coding agents, log in to providers, or manage provider
credentials.

## Does context-eval call hosted services?

No. The runner, reports, exports, static UI, and local app mode are local-first.
The local app binds to loopback and uses local files and local run artifacts.

## Can the static UI run agents?

No. The static UI is an offline, self-contained HTML export. It can inspect
config and run artifacts and generate downloadable YAML, but it does not save
files, run validation commands, or start agents.

## How is the local app different from the static UI?

The local app is an explicit loopback mode. It can save selected local files,
run side-effect-free preflight checks, start local evaluations after explicit
confirmation, stream logs, inspect artifacts, and produce exports. It is still
local and does not become a hosted service.

## What artifacts should users inspect first?

Start with `report.md`, `context-eval compare`, and `context-eval inspect-run`
for the run overview, variant summaries, risk signals, and confidence notes.
Then inspect `results.jsonl`, `run_manifest.json`, validation logs, patches,
stdout and stderr logs, and retained workspaces for cases that need deeper
review. This artifact-only reporting model keeps conclusions grounded in what
the local run recorded.
