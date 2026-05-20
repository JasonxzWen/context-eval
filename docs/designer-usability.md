# Designer Usability For Context Evaluation

This document defines the first usability slice for game designers and other
non-technical reviewers who use context-eval to evaluate context quality.

## Product Purpose

context-eval compares different local context environments by running the same
coding-agent tasks end to end and collecting evidence from the resulting local
artifacts. The comparison target is the context package, not the agent brand.

In the first designer-facing version, users should be able to answer three
questions without editing YAML directly:

1. What task should the coding agent complete?
2. Which context package should be compared, mainly `AGENTS.md` and `skills`?
3. Did the result satisfy the task, based on artifacts and manual feedback?

## User Scope

The first version is for designers who can describe desired behavior and review
results, but should not need to know the internal schema.

They can:

- configure a test case with a title, task instruction, expected result,
  acceptance points, expected files, and validation commands;
- configure context packages as named schemes that copy local `AGENTS.md` files
  and `skills` folders into the run workspace;
- select which tasks and context schemes to run;
- review each result, inspect patch/log/evidence artifacts, and save manual
  feedback.

They do not need to:

- understand YAML overlays, telemetry internals, or benchmark terminology;
- read unstructured agent logs to infer key metrics;
- use hosted services, public leaderboards, or automatic LLM judges.

## Terminology

The UI should prefer the following labels:

| Internal term | Designer-facing term | Meaning |
| --- | --- | --- |
| task | 测试用例 | One agent assignment to run under every selected context scheme. |
| prompt | 任务说明 | The instruction passed to the coding agent. |
| expected_outcome | 期望结果 | What a successful result should look like. |
| acceptance_points | 验收点 | Human-readable checks for manual review. |
| validation_commands | 自动验收命令 | Project tests or scripts run after the agent finishes. |
| variant | 上下文方案 | A named context package to compare. |
| overlay | 上下文资料 | Local files copied into the run workspace. |
| `AGENTS.md` | Agent 工作说明 | Instructions the coding agent reads in the workspace. |
| `skills` | 技能包 | Reusable task knowledge available to the coding agent. |
| hard_evaluation | 硬性检查 | Deterministic local checks; not a full quality score. |
| soft_evaluation | 复核材料 | Optional payload-only material for future review. |
| manual_review | 人工反馈 | Human conclusion and notes saved with the result. |
| telemetry | 执行指标 | Duration, tokens, tool calls, command calls, status, and evidence gaps. |

## UI Requirements

### Test Case Configuration

The test-case panel must explain that a case is the same assignment repeated
under each selected context scheme. It should show the core fields first:

- task ID and title;
- category and difficulty;
- task instruction;
- expected result summary;
- acceptance points;
- expected changed files;
- validation commands.

Advanced deterministic checks and review rubrics stay visible, but the copy must
state that they support evidence gathering and do not prove absolute task
correctness.

### Context Scheme Configuration

The context-scheme panel must explain that a scheme is a local package of
agent-facing context. It should make `AGENTS.md` and `skills` first-class in the
copy, because those are the primary comparison materials for this version.

For each copied path, the UI should identify common sources:

- `AGENTS.md` paths as Agent 工作说明;
- paths containing `skills` as 技能包;
- all other paths as 其他上下文资料.

The UI must not imply that context-eval reads user credentials or global
sensitive logs. Any future Codex or agent log import must be explicit,
path-selected, read-only, and explainable.

### Manual Feedback

The result-detail panel must make manual feedback a primary action. It should
show:

- the case status, validation status, confidence, telemetry status, and hard
  check result;
- a feedback form with result conclusion, reviewer confidence, reviewer name,
  and notes;
- a note template that asks reviewers to record whether the result met the task,
  what evidence they checked, and what issue remains.

Manual feedback is evidence. It is not an automatic score and must not silently
override artifact-based metrics.

### Comparison Results

The result view must preserve the product boundary:

- local-only and artifact-based;
- not a public benchmark;
- not an agent leaderboard;
- no automatic OpenAI, Claude, or other LLM judge;
- validation passing means configured checks passed, not that the task is
  absolutely correct;
- any future AI arbitration is optional soft evidence, disabled by default, and
  excluded from comprehensive ranking.

## Acceptance Criteria

This slice is acceptable when:

1. A designer can open the local app and understand that context-eval compares
   context quality through local coding-agent runs.
2. The main workflow labels are 测试用例, 上下文方案, and 人工反馈.
3. Test-case fields include hover or inline help for task instruction, expected
   result, acceptance points, expected files, validation commands, hard checks,
   and review rubrics.
4. Context schemes explain `AGENTS.md` and `skills`, and overlay rows display
   whether each row is Agent 工作说明, 技能包, or 其他上下文资料.
5. Manual feedback explains what reviewers should record and keeps the saved
   fields artifact-based.
6. Result guidance states that this is local-only, not a public benchmark, not
   an agent leaderboard, and not an automatic LLM judge.
7. Existing structured save behavior still preserves unknown YAML fields.
8. Frontend unit tests, build, and browser acceptance pass.
