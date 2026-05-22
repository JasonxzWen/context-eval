# Real Project Evaluation Support Plan

## Goal

Make context-eval practical for private production repositories where a
non-technical planner compares two context packages, such as an older
`AGENTS.md` against a newer `AGENTS.md` plus project wiki docs.

The first supported real-project workflow should let a planner configure:

1. the target repository path;
2. two or more context packages built from local `AGENTS.md`, `skills`, and
   docs folders;
3. task cases that start from a known Git ref;
4. expected answers or real fix references for later review;
5. local validation commands and optional AI arbitration runner output;
6. manual feedback after reviewing each case result.

## Product Boundary

This capability stays inside the existing context-eval boundary:

- local-only and artifact-based;
- no public benchmark;
- no agent leaderboard;
- no hidden hosted judge calls;
- no provider credential or global log reading;
- no automatic commits to the target repository;
- no claim that validation success proves absolute correctness.

Codex telemetry must come from structured local run artifacts such as
`codex exec --json` JSONL output. Missing telemetry remains `null` and is shown
as an evidence gap. Reading user-selected external Codex logs is a future
explicit, read-only import path, not a default behavior.

## Task Case Types

The planner-facing task type is metadata. It helps UI templates, filtering, and
review. It must not change runner semantics by itself.

Supported first-pass values:

| Value | Planner label | Purpose |
| --- | --- | --- |
| `compile_diagnosis` | Compile error diagnosis | Paste a compiler or build error and ask the agent to identify the cause. |
| `bugfix` | Known bug fix | Start before a known fix and ask the agent to repair the bug. |
| `incident` | Incident diagnosis and fix | Start before a known fix, provide a symptom, and ask for root cause plus repair. |
| `feature` | Feature work | Start before a known change and ask for a small implementation. |
| `custom` | Custom case | Keep existing behavior for one-off tasks. |

Existing `task.repo_ref` remains the case starting version. If it is empty, the
case uses `repo.base_ref`. The UI should label it as "start from version" rather
than exposing Git terminology first.

## Reference Evidence

Real projects often have a known answer, a real fix commit, or a maintainer note.
The task schema should allow this evidence to be recorded without sending it to
the coding agent by default.

First-pass fields:

```yaml
tasks:
  - id: "compile-error-case-1"
    title: "Compile error diagnosis"
    case_type: "compile_diagnosis"
    repo_ref: "before-fix-commit"
    prompt: |
      Diagnose this compile error:
      <paste error here>
    expected_outcome:
      summary: "The root cause matches the maintainer-provided answer."
      acceptance_points:
        - "Identifies the actual failing module."
        - "Explains the root cause."
    reference_evidence:
      summary: "Maintainer-provided true result."
      fix_ref: "real-fix-commit-or-pr"
      files:
        - "src/example/File.cpp"
      notes:
        - "Do not include this in the agent prompt by default."
```

`reference_evidence` is for human review and optional soft arbitration payloads.
It should appear in exported artifacts and local UI detail panels, but the
runner must not append it to the agent prompt unless a future explicit option is
added.
In other words, reference evidence means not sending it to the coding agent by
default.

## Metrics

Required hard metrics:

- total case duration;
- agent command duration when available;
- status, timeout, exit code, stdout, stderr, and error reason;
- token counts from structured telemetry: input, cached input, output, total,
  and reasoning output;
- tool calls and command calls from structured telemetry;
- changed files, insertions, deletions, and touched paths;
- validation command status;
- hard evaluation status and score when configured.

## Soft Arbitration

Soft arbitration can either stop at payload generation or run an explicit local
arbitration executor. When no arbitration executor is chosen, runner mode uses
the same executor as the evaluated case.

The payload may include:

- task prompt;
- task type;
- expected outcome;
- reference evidence;
- patch excerpt and touched paths;
- validation and hard evaluation summary;
- Codex telemetry and evidence gaps;
- manual review fields when present.

The arbitration runner must save stdout, stderr, exit status, duration, raw
result output, and a parsed JSON result when available. It must not infer a
score from unstructured prose. The resulting score is optional soft evidence and
is excluded from the primary comparison ranking unless the maintainer changes
that boundary.

## UI Shape

The planner should see a short, task-oriented flow:

1. **Project setup**: open an existing local Git repository, or clone a
   user-provided Git URL into the local evaluation workspace. Show Git, Codex
   CLI, and repository readiness before running. Do not read credentials or
   global logs.
2. **Test cases**: choose case type, name the case, fill "AI task prompt", fill
   "how humans judge it", optionally set start version and reference evidence.
3. **Context packages**: add one package for old `AGENTS.md`, another for new
   `AGENTS.md` plus docs/wiki. Use labels such as "old context" and "new
   context" instead of unexplained baseline language.
4. **Runner**: show where the Codex CLI command is configured, whether
   structured JSONL capture is enabled, and which executor performs optional AI
   arbitration.
5. **Run and review**: show case matrix, hard metrics, evidence gaps, reference
   evidence, optional AI arbitration output, and the manual 1-5 feedback form.

Default screens should be concise. Reference evidence, automatic checks, and
soft arbitration details can live in clear expandable sections.

## Implementation Slices

1. Document the real-project workflow, task fields, non-goals, and acceptance
   gates.
2. Add schema and editor support for `case_type` and `reference_evidence`.
3. Surface those fields in run plans, soft evaluation payloads, exports, and
   local UI detail panels.
4. Add UI templates for compile diagnosis, known bug fix, incident fix, and
   feature work.
5. Add explicit local AI arbitration runner support.
6. Add E2E coverage for configuring a real-project-style comparison and saving
   human feedback.

## Acceptance

- A planner can configure old-context vs new-context runs without editing YAML.
- A planner can open a local repo or clone a Git URL from the local app before
  configuring cases.
- Git, Codex CLI, and repository readiness are visible before a run.
- Each case can start from its own Git ref.
- Reference evidence is saved locally, exported, and available for review, but
  not sent to the agent prompt by default.
- Codex metrics are captured only from structured local artifacts; missing data
  is shown as an evidence gap.
- AI arbitration runner output is saved as local soft evidence and is never the
  truth source by itself.
- Unit tests, frontend tests, and Playwright E2E tests cover the workflow.
