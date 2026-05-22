# Real Project GUI Workflow Design

## Goal

Make the real-project workflow usable when the author wants to evaluate a
private production repository such as SeriaServer. The first implementation
focuses on the easy and medium items that remove setup friction:

- open an existing local Git repository from the UI;
- clone a Git URL into the local evaluation workspace from the UI;
- check local Git, Codex CLI, and repository readiness before running;
- keep the existing case, context package, Codex telemetry, AI arbitration, and
  manual feedback features visible without adding hosted services.

## Research Notes

Codex CLI exec mode supports non-interactive runs and `--json` JSONL output for
programmatic parsing. The documented workflow also supports
`--output-last-message` for capturing the final response and `-C/--cwd` for a
working directory. The current upstream JSONL implementation emits typed events
such as `thread.started`, `turn.started`, `turn.completed`, `turn.failed`,
`item.started`, `item.completed`, and `error`. `turn.completed` includes usage
fields for input, cached input, output, and reasoning output tokens. Command
execution, file changes, MCP tool calls, and final agent messages are emitted as
typed thread items.

Local verification on this machine found a blocker: `codex.exe` exists but
`codex --version` and `codex exec --help` return `Access is denied`. The product
must therefore treat Codex availability as a local environment check, not as an
assumption, and tests should use fixtures for Codex JSONL parsing.

Sources:

- <https://www.mintlify.com/openai/codex/cli/exec>
- <https://www.mintlify.com/openai/codex/concepts/non-interactive-mode>
- <https://raw.githubusercontent.com/openai/codex/main/codex-rs/exec/src/exec_events.rs>
- <https://raw.githubusercontent.com/openai/codex/main/codex-rs/exec/src/event_processor_with_jsonl_output.rs>

## Scope

### In Scope

1. Add local app APIs for:
   - environment checks;
   - opening an existing project path;
   - cloning a user-provided Git URL into a safe workspace subdirectory.
2. Add planner-facing UI for:
   - existing local repo path;
   - Git URL clone;
   - compact environment check results.
3. Update docs and UI copy so each step says what it does and why.
4. Add unit and E2E tests for setup paths and environment checks.

### Out Of Scope

- No Codex install button.
- No Codex login or account management.
- No price-table-driven cost estimation.
- No hidden hosted AI judge.
- No automatic target-repository commit, push, tag, release, or deployment.
- No reading global Codex logs or credentials.

## API Design

### `GET /api/environment`

Returns a local readiness summary.

Optional query parameters:

- `repo_path`: project path to inspect. If omitted, use the loaded config repo
  when available.
- `config_path`: config file to inspect when available.

Response shape:

```json
{
  "ok": true,
  "checks": [
    {
      "id": "git",
      "label": "Git",
      "status": "ok",
      "summary": "git version 2.45.2.windows.1",
      "detail": null
    }
  ],
  "repo": {
    "path": "D:/project",
    "is_git_repo": true,
    "branch": "main",
    "head": "abc123",
    "dirty_file_count": 0
  }
}
```

Statuses are `ok`, `warning`, or `error`. Dirty repositories are warnings, not
hard blockers, because context-eval runs from Git refs in isolated workspaces.

### `POST /api/workspace/project`

Existing path mode:

```json
{ "repo_path": "D:/SeriaServer", "overwrite": false }
```

Clone mode:

```json
{
  "repo_url": "https://code.byted.org/oasis/SeriaServer.git",
  "clone_dir": "SeriaServer",
  "overwrite": false
}
```

Clone mode runs local `git clone` into:

```text
<evaluation-workspace>/repositories/<clone_dir>
```

The clone directory must be a safe relative path. Existing non-empty targets are
rejected. HTTP(S) URLs with embedded credentials are rejected; users must rely
on their local Git authentication.

## UI Design

The top setup area should have two compact cards:

- "打开本地项目": paste a local repository path, then create the evaluation
  workspace.
- "从 Git URL 克隆": paste a Git URL, choose a local folder name, then clone and
  create the evaluation workspace.

Below the cards, show "本机检查" as a compact status list:

- Git;
- Codex CLI;
- selected repository.

Each row should use one line by default: status, short message, and optional
details only when needed. Avoid hover-only explanations.

## Grill-Me Pressure Test

Plan summary: the smallest useful version is not a full no-code product; it is a
local project setup and readiness layer that connects the existing YAML-backed
engine to a planner-friendly UI. The existing runner and artifact model remain
the source of truth.

Assumptions tested:

- Authors can use local Git authentication; context-eval must not collect it.
- A dirty source repository should be visible but not necessarily block a run.
- Git URL clone should write only inside the evaluation workspace by default.
- Codex availability varies by machine, so it should be reported as a check.

Key decision: clone targets are constrained to the evaluation workspace. This is
less flexible than cloning directly to `D:\SeriaServer`, but it prevents the
local web UI from writing arbitrary filesystem locations. Users who already
have a production checkout can still use the local path mode.

## Acceptance

- Environment check API reports Git, Codex CLI, and repository state without
  running agents or validation commands.
- Existing local repo setup still works.
- Git URL clone setup works with a local `file://` fixture in automated tests.
- Credential-bearing clone URLs are rejected.
- Unsafe clone directory paths are rejected.
- UI can clone/open, then show the normal case/context/AI/run workflow.
- Frontend unit tests and Playwright E2E cover both setup paths.
