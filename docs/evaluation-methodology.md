# Evaluation Methodology

[Back to documentation index](index.md).

context-eval evaluates context assets, not absolute agent intelligence. The
core question is whether changing the context available to a configured local
coding agent changes task outcomes in a real Git repository.

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

Human review remains necessary because validation commands may be incomplete,
too broad, too narrow, flaky, or unrelated to the task's real acceptance
criteria. Reviewers should inspect patches, validation logs, stdout and stderr,
prompts, retained workspaces, reports, and exports before acting on results.

The artifact model is designed to make that review reproducible and debuggable.

## Why No LLM Judge As Truth

The current project scope avoids treating an LLM judge as the main correctness
source. A judge can be useful as a secondary review aid in some systems, but it
would introduce another model-dependent signal that may not reflect the target
repository's tests, invariants, or maintainers' acceptance criteria.

context-eval keeps correctness grounded in validation commands, recorded local
artifacts, and human engineering review.
