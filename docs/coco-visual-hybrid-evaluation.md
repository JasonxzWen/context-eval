# Coco-first Visual Hybrid Evaluation

This spec defines the next local app capability for authoring and reviewing a
complete Coco-focused context-eval workflow. The workflow remains local-first
and artifact-based: context-eval compares context variants in a real local Git
repository and reports local observations, not absolute agent rankings.

## User Workflow

1. Open the loopback local app for an evaluation workspace.
2. Configure the project repo path, base ref, task file, output directory, and
   validation commands.
3. Configure a Coco profile such as
   `coco -y --query-timeout 10m --bash-tool-timeout 5m -p "{prompt}"`.
4. Configure context variants and overlays.
5. Author tasks with prompts, category, difficulty, and optional repo refs.
6. Add expected outcomes, deterministic hard checks, and optional soft
   evaluation payload settings.
7. Run side-effect-free preflight.
8. Review the task x variant x trial run plan and explicitly confirm execution.
9. Inspect results, hard-check evidence, soft payload status, metrics, patches,
   logs, and exports from local run artifacts.

## Coco-first Agent Profile Configuration

Coco is a first-class profile kind for this workflow:

```yaml
agents:
  coco:
    kind: "coco"
    command: "coco -y --query-timeout 10m --bash-tool-timeout 5m -p \"{prompt}\""
    timeout_minutes: 60
    network: "disabled"
    telemetry:
      collector: "json-file"
      file: "telemetry.json"
```

`kind: "coco"` classifies the local command for validation, presets, and UI
copy. It does not install Coco, does not manage Coco credentials, or call
hosted APIs.
Preflight may check whether the first executable token is available when
`--check-agents` or local app preflight is requested, but it must not run Coco.
The Coco-focused unattended template uses Coco's `-y` mode plus query and bash
timeouts so Coco can edit files and run shell commands without a prompt during a
local evaluation run. Users who want a narrower approval boundary can replace
`-y` with their chosen `--allowed-tool ...` flags in `agents.coco.command`;
context-eval records and runs the command template but does not grant Coco
permissions outside that user-owned command.

Coco telemetry is optional. If Coco writes a structured JSON telemetry artifact,
the existing `json-file` collector may normalize fields such as
`agent_duration_seconds`, token counts, `tool_call_count`,
`tool_calls_by_name`, and `reasoning_step_count`. Missing telemetry remains
unavailable; context-eval does not infer token counts, tool counts, reasoning
steps, or other metrics from unstructured logs.

## Task Authoring Model

Existing tasks remain valid. New fields are optional:

```yaml
tasks:
  - id: "mail-expire-attachment"
    title: "Fix expired mail attachment claim"
    repo_ref: "abc123"
    prompt: |
      Fix the bug where expired mail attachments can still be claimed.
      Keep the change minimal and follow existing module conventions.
    category: "gameplay"
    difficulty: "medium"
    expected_outcome:
      summary: "Expired mail attachments cannot be claimed; valid attachments still work."
      acceptance_points:
        - "Expired attachments cannot be claimed."
        - "Unexpired attachments remain claimable."
    hard_evaluation:
      enabled: true
      require_validation_pass: true
    soft_evaluation:
      enabled: true
      mode: "payload-only"
```

Unknown task fields must not be silently dropped by local app save/reload
flows. Structured editors can expose the most important fields first, but the
raw `tasks.yaml` editor remains the compatibility fallback.

## Expected Outcome Model

`expected_outcome` describes what the user expects from the patch:

- `summary`: short human-readable outcome.
- `files`: expected file-level changes with `path`, `change_type`,
  `must_change`, `expected_snippets`, and `forbidden_snippets`.
- `forbidden_paths`: repository-relative paths that should not change.
- `acceptance_points`: concise behavior or validation expectations.

All repository-relative path fields reject absolute paths and traversal
segments. The first implementation supports exact path matching for evaluation
checks. Glob-style patterns can be documented and added later only when covered
by tests.

## Hard Evaluation Model

`hard_evaluation` computes deterministic checks from local artifacts:

- validation passed when `require_validation_pass` is true;
- required paths were changed;
- forbidden paths were not touched;
- changed file count is within `max_changed_files`;
- expected snippets are present in retained workspace files or patch text;
- forbidden snippets are absent from retained workspace files or patch text;
- optional insertion/deletion bounds when configured;
- timeout and agent failure are reflected as failed checks when relevant.

Hard evaluation writes one sidecar per case:

```text
artifacts/<case_id>/hard_evaluation.json
```

The sidecar contains schema version, case identity, pass/fail status, score,
max score, check rows, evidence, and summary. `results.jsonl`, reports, exports,
and the local app expose a compact summary while preserving old row parsing.

## Optional Soft Evaluation Model

The first implementation supports payload generation only:

```yaml
soft_evaluation:
  enabled: true
  mode: "payload-only"
  max_score: 10
  rubric:
    - name: "requirement_match"
      weight: 4
      description: "Patch satisfies the requested behavior."
    - name: "minimality"
      weight: 2
      description: "Patch avoids unrelated changes."
```

The runner writes:

```text
artifacts/<case_id>/soft_evaluation_payload.json
```

The payload includes the task prompt, expected outcome summary, acceptance
points, rubric, changed files, patch excerpt, validation status, hard
evaluation summary, and relevant log/artifact paths. context-eval does not call
OpenAI, Claude, or other hosted model APIs directly and does not require
provider keys. Soft score is optional evidence and is not the correctness
source. This workflow does not call hosted model APIs directly.

## Local App UI Workflow

The local app exposes these workflow sections:

- Project: repo path, base ref, tasks file, and output directory.
- Coco Agent: command, timeout, telemetry collector, and executable preflight
  status.
- Context Variants: names, descriptions, and overlays.
- Tasks: task list, prompt editor, category, difficulty, and repo ref.
- Expected Outcome: summary, acceptance points, required files, forbidden
  paths, and snippet expectations.
- Hard Evaluation: enablement, validation requirement, changed-file limit,
  path checks, and snippet checks.
- Soft Evaluation: enablement, payload-only mode, and rubric.
- Run Plan: selected Coco profile, planned matrix, and hard/soft flags.
- Run Execution: explicit confirmation, progress, logs, stop state, and errors.
- Results: case status, validation, hard score/checks, soft payload/result
  status, metrics, changed files, patches, logs, and sidecar links.

The static UI remains export-only and cannot run agents or write files. Local
app execution still requires explicit confirmation.

## Local App API Workflow

The local app API extends existing endpoints without adding a hosted service:

- load config/tasks with expected outcome and evaluation fields;
- save config/tasks inside the workspace and preserve unknown fields;
- validate expected outcome and evaluation paths during save/preflight;
- include Coco profile, expected outcome summary, and hard/soft flags in run
  planning;
- include hard evaluation and soft payload/result status in results;
- read `hard_evaluation.json` and `soft_evaluation_payload.json` through the
  existing safe artifact endpoint.

Path safety stays strict: config writes remain inside the workspace, artifact
reads remain inside the selected run directory, and expected paths are
repository-relative without traversal.

## Artifact Schema Additions

New per-case sidecars:

- `artifacts/<case_id>/hard_evaluation.json`
- `artifacts/<case_id>/soft_evaluation_payload.json`

`results.jsonl` may include compact fields:

- `hard_evaluation_status`
- `hard_evaluation_score`
- `hard_evaluation_max_score`
- `hard_evaluation_passed_checks`
- `hard_evaluation_failed_checks`
- `hard_evaluation_path`
- `soft_evaluation_status`
- `soft_evaluation_payload_path`
- `soft_evaluation_result_path`

Older rows omit these fields and parse with unavailable defaults.

## Non-goals

- Do not add adapters for Codex CLI, Claude Code, traecli, or other agents in
  this capability.
- Do not install Coco automatically.
- Do not manage Coco credentials.
- Do not call hosted model APIs directly.
- Do not add a hosted dashboard, global leaderboard, or hosted score service.
- Do not make an LLM judge the only correctness source.
- Do not run external services in tests.
- Do not commit generated run artifacts.
- Do not infer token counts, tool counts, or reasoning steps from unstructured
  logs.

## Test Plan

- Model tests for old tasks, new fields, path safety, and `kind: "coco"`.
- Config/local app tests proving save/reload preserves unknown task fields.
- Runner tests for hard evaluation pass/fail, required paths, forbidden paths,
  snippet checks, validation requirements, and sidecar artifacts.
- Runner tests for soft payload-only generation.
- Local app tests for plan flags, results summaries, and safe sidecar reads.
- Report/export tests for stable hard/soft fields and old row compatibility.
- Frontend tests for Coco, expected outcome, hard/soft sections, run plan, and
  result review.
- Local-e2e with the fixture repository and fake local agent; no real Coco.
