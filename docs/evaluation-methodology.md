# Evaluation Methodology

[Back to documentation index](index.md).

context-eval evaluates context assets, not absolute agent intelligence. The
core question is whether changing the context available to a configured local
coding agent changes task outcomes in a real Git repository.

It is a local Context A/B Testing Framework for real Git repositories, not a
benchmark or absolute ranking.

## What Is Being Evaluated

The evaluated variable is the context variant overlay. Examples include
`AGENTS.md`, local docs, DeepWiki exports, skills, rules, prompt templates, and
repo-specific guidance files.

The result should be read as an observation about that context asset under the
recorded setup. It should not be generalized into a global statement about an
agent, model, provider, or tool family.

## Controlled Variables

Useful comparisons keep these inputs stable:

- target repository and local repository state;
- task prompt, metadata, and optional `repo_ref`;
- configured agent command or selected agent profile;
- validation commands and validation timeouts;
- context-eval version and result schema version;
- trial count and planned case matrix;
- local machine and toolchain conditions where practical.

These controls are recorded through config, tasks, result rows, hashes,
manifests, logs, and reports so reviewers can inspect what actually ran.

## Experimental Variable

The experimental variable is the selected context variant overlay. Each case
uses an isolated workspace so one variant's files do not mutate another
variant's workspace.

When comparing variants, keep the task, repo ref, agent command, validation
commands, trials, and cleanup policy aligned unless the change itself is the
subject of the evaluation.

## Compare Baseline

The compare baseline is the variant used as the reference for a local
task/agent/trial comparison. It is not a global winner, a default truth source,
or a leaderboard anchor. In the local app it defaults to the `baseline` variant
when present, otherwise the first available variant, and users can choose a
different reference variant.

For each task, agent, and trial group, context-eval compares the selected
baseline against the other selected variants. The compare summary reports the
baseline variant, the comparison variant, validation delta, hard-check delta,
token delta when available, and any evidence gaps that make the comparison
low-confidence.

## Correctness Layers

The evaluation model has three layers:

1. Agent execution artifacts: status, timeout, exit code, patch, touched paths,
   logs, diff stats, and optional structured telemetry.
2. Deterministic project checks: validation commands and hard evaluation rules
   derived from task configuration and local artifacts.
3. Optional soft review payloads: structured JSON for later human or local
   judge review.

Validation commands and hard evaluation are the primary machine-checkable
signals. Soft grading is optional review evidence and does not replace tests,
hard checks, or human review.

## Validation Defines Confidence

Validation commands are the project-specific acceptance criteria. They convert
an agent-produced patch into a stronger engineering signal by checking behavior
with the target repository's own tools.

context-eval confidence levels are intentionally conservative:

- `high`: validation commands exist and passed.
- `medium`: validation commands exist and one or more failed.
- `low`: no validation commands were available.

Patch size, touched paths, timing, and logs can help reviewers inspect a case,
but they do not establish correctness on their own.

## Hard Checks

Hard checks are deterministic and local. They can require validation success,
required changed paths, forbidden paths, changed-file limits, expected snippets,
forbidden snippets, simple diff-stat bounds, and agent completion. Checks read
only local case artifacts such as `results.jsonl`, patches, touched paths,
validation results, and retained workspaces.

The hard score is the number of passed deterministic checks divided by the
number of scoreable deterministic checks. Skipped checks do not enter the
denominator. This is not a combined quality score and should not be added to
validation confidence or manual review as a single overall score.

When a hard check cannot be evaluated because a workspace was cleaned up and
the patch does not contain enough evidence, the check is marked `skipped` with
an explicit message instead of guessing.

## Optional Soft Grading

Soft grading starts as `payload-only`. context-eval writes a
`soft_evaluation_payload.json` sidecar that includes the prompt, expected
outcome, rubric, changed files, patch excerpt, validation status, hard
evaluation summary, and artifact links.

The first implementation does not call hosted model APIs, does not require
provider keys, and does not make soft scores mandatory for pass/fail.

Manual review is separate from soft payload generation. A saved manual review
records the human reviewer's evidence, confidence, and notes; it is not an
automatic score and does not prove absolute task correctness.

## Telemetry And Metrics

Telemetry is optional and must come from structured local artifacts. If Coco or
another local agent writes JSON telemetry, context-eval can normalize fields
such as duration, token counts, tool calls, and reasoning step count. Missing
metrics remain unavailable. context-eval does not infer token counts, tool
counts, or reasoning steps from unstructured logs.

## No-Validation Cases

No-validation cases remain low confidence because context-eval cannot determine
whether the patch satisfied the task. They may still be useful for prompt
inspection, diff review, failure triage, or building an initial task suite, but
they should not be treated as proof of correctness.

## Repeated Trials

Repeated trials help observe nondeterminism. If a task succeeds in some trials
and fails in others, that is a useful stability signal for the selected repo,
task, context variant, agent command, and validation setup.

Repeated trials still do not create absolute claims. They show variation inside
the recorded local experiment, not a general ranking.

## Artifacts And Human Review

Human review remains necessary because validation commands and hard checks may
be incomplete, too broad, too narrow, flaky, or unrelated to the task's real
acceptance criteria. Reviewers should inspect patches, validation logs, stdout
and stderr, prompts, retained workspaces, reports, exports, and sidecars before
acting on results.

The artifact model is designed to make that review reproducible and debuggable.

## Why No LLM Judge As Truth

The current project scope avoids treating an LLM judge as the main correctness
source. A judge can be useful as a secondary review aid in some systems, but it
would introduce another model-dependent signal that may not reflect the target
repository's tests, invariants, or maintainers' acceptance criteria.

context-eval keeps correctness grounded in validation commands, recorded local
artifacts, and human engineering review.
