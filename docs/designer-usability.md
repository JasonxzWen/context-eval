# Designer Usability For Context Evaluation

This document defines the planner-facing workflow for game designers and other
non-technical reviewers who use context-eval to compare context quality.

## Product Purpose

context-eval answers one question: when the same coding-agent task runs against
different context packages, which package helps the agent finish the task more
reliably and efficiently?

The comparison target is the context package, usually `AGENTS.md`, project docs,
wiki exports, and `skills`. The output is local evidence for review. It is not a
public benchmark or an agent leaderboard.

The product boundary is local-only and artifact-based: not a public benchmark,
not an agent leaderboard, and no hidden OpenAI, Claude, or other LLM judge calls.
validation passing means configured checks passed, not that the task is
absolutely correct. AI arbitration output is secondary soft evidence.

## First-Use Workflow

The first screen should let a planner move through these steps without editing
YAML:

1. Open the project: choose an existing local Git repository or clone a Git URL
   into the evaluation workspace.
2. Write evaluation cases: describe what the AI must do, where the case starts,
   what the real answer is, and how a human should judge the result.
3. Prepare comparison materials: create one package for the old context and one
   package for the new context, such as optimized `AGENTS.md` plus `docs`.
4. Choose the local AI command: for Codex CLI, prefer `codex exec --json` so
   context-eval can capture structured evidence.
5. Run local checks: verify Git, Codex CLI, repository state, task refs, overlay
   paths, and output paths before starting a run.
6. Review results: inspect hard metrics, validation, AI arbitration,
   reference evidence, patch/log artifacts, and manual feedback.

## User Scope

The first version is for users who can describe a task and judge a result, but
should not need to know the internal schema.

They can:

- open an existing local repository or clone a private repository by URL through
  the local app;
- configure cases for compile diagnosis, known bug fixes, incident diagnosis
  and repair, feature work, and custom tasks;
- configure old-context versus new-context packages from local files and
  folders;
- select a local AI command, including Codex CLI;
- see whether required local tools are available before running;
- review each result and save a one-to-five human rating with notes.

They do not need to:

- edit YAML directly for the common path;
- understand overlay internals, telemetry schemas, or benchmark terminology;
- read unstructured agent logs to infer token or tool-call metrics;
- use hosted services, public leaderboards, or hidden LLM judges.

## Terminology

The UI should prefer these labels. A context package, not the agent brand, is
the comparison target.

| Internal term | UI label | Meaning |
| --- | --- | --- |
| task | 测试用例 / 评测题目 | One assignment repeated under each selected context package. |
| prompt | AI 要做什么 | The instruction sent to the coding agent. |
| case_type | 题目类型 | Compile diagnosis, bug fix, incident fix, feature work, or custom. |
| repo_ref | 起始版本 | The Git version used to create this case's isolated workspace. |
| expected_outcome | 人工验收目标 | What a successful result should look like for human review. |
| acceptance_points | 验收点 | Checklist items used by human feedback and optional arbitration payloads. |
| reference_evidence | 真实对照材料 | True answer, real fix ref, important files, or maintainer notes. |
| validation_commands | 自动验收命令 | Project tests or scripts run after the agent finishes. |
| variant | 上下文方案 / 对比资料 | A named context package to compare. |
| overlay | Agent 工作说明 / 技能包 / 资料 | A local `AGENTS.md`, `skills` folder, docs folder, or wiki export copied into the run workspace. |
| agent | 本地 AI | The local command that runs the coding agent. |
| hard_evaluation | 硬性检查 | Deterministic local checks; evidence, not absolute correctness. |
| soft_evaluation | AI 仲裁 | Default same-agent local arbitration; never the truth source by itself. |
| manual_review | 人工反馈 | Human conclusion, rating, confidence, and notes saved with the result. |
| telemetry | 硬指标 | Duration, tokens, tool calls, command calls, status, and evidence gaps. |

Avoid using "baseline" as the only explanation. If the name appears, explain it
as "the old or default context package used for comparison".

## UI Requirements

### Project Setup

The local app must support two setup paths:

- Existing local repo: the user selects or pastes a local Git repository path.
- Clone from Git URL: the user pastes a Git URL and chooses a local folder name;
  context-eval runs local `git clone` into the evaluation workspace.

The app must not read or store credentials. If a private repository needs
authentication, local `git` should use the user's existing Git authentication and
surface any failure message. URLs containing embedded credentials must be
rejected with a clear explanation.

### Environment Checks

Before a real run, the UI must show compact checks for:

- `git` availability;
- `codex` availability and whether `codex --version` / `codex exec --help` can
  run;
- whether the selected project is a Git repository;
- current branch, commit, and dirty-file count when available;
- configured task refs, context paths, agent command variables, and output path
  safety through existing preflight.

Warnings should not claim the project is unusable unless a run would fail. For
example, a dirty repository should be visible as a warning because context-eval
creates isolated workspaces from Git refs.

### Evaluation Cases

The case editor should keep the common fields visible:

- title;
- case type;
- AI task prompt;
- start version;
- human acceptance target and AI arbitration basis;
- reference answer or real fix evidence;
- validation command.

Advanced hard checks may stay behind an expandable section. AI arbitration is
not a planner setting in the common UI: it runs after the coding agent with the
same local AI and the same case workspace. The copy must make clear that
reference evidence is not sent to the coding agent by default.

### Context Packages

The context package editor should explain the concrete action:

- version 1 can point to the old `AGENTS.md`;
- version 2 can point to the optimized `AGENTS.md`, `docs`, wiki export, and
  `skills`;
- each row copies a local file or folder into the temporary run workspace.

The UI must not imply that context-eval reads global Codex logs, secrets, or
credentials.

### Results And Feedback

The result detail should show:

- final status and duration;
- token usage, cached input tokens, output tokens, reasoning tokens;
- tool-call count and command-call count;
- changed files and touched paths;
- validation status;
- hard-check status and score;
- AI arbitration result as soft evidence;
- evidence gaps such as missing Codex JSONL or final message;
- manual one-to-five rating, conclusion, confidence, reviewer, and notes.

## Non-Goals

This usability slice does not add:

- public benchmark publishing;
- agent leaderboard ranking;
- automatic target-repository commits;
- hosted LLM judge calls hidden behind the UI;
- Codex CLI installation or login management;
- provider credential storage;
- price-table-driven cost estimation.

## Acceptance Criteria

This slice is acceptable when:

1. A planner can open the local app and understand that the product compares
   context packages for the same coding-agent tasks.
2. A planner can create a real-project workspace from either a local repo path
   or a Git URL without editing YAML.
3. The UI shows local environment checks for Git, Codex CLI, and the selected
   repository.
4. The case editor supports start version, reference evidence, validation, hard
   checks, default AI arbitration basis, and manual-review goals.
5. The context editor makes old `AGENTS.md` versus new `AGENTS.md` plus docs or
   skills easy to configure.
6. Result views show hard metrics, Codex evidence gaps, AI arbitration,
   and manual feedback.
7. Missing telemetry remains missing and is shown as an evidence gap.
8. Unit tests, frontend tests, and Playwright E2E tests cover the setup and
   review workflow.
