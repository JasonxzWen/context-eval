from pathlib import Path


def test_agent_profiles_spec_documents_noninteractive_contract() -> None:
    text = Path("docs/agent-profiles.md").read_text(encoding="utf-8")

    for heading in [
        "## User Contract",
        "## Compatibility",
        "## Profile Model",
        "## Command Template Contract",
        "## Built-In Presets",
        "## Agent Matrix Execution",
        "## Reporting Behavior",
        "## Failure Modes",
        "## Non-Goals",
        "## Test Plan",
    ]:
        assert heading in text

    for term in [
        "Codex CLI",
        "codex exec --json",
        "--output-last-message",
        "codex-events.jsonl",
        "codex-final-message.md",
        "Claude Code",
        "traecli",
        "coco",
        "custom",
        'traecli -p "{prompt}"',
        'coco -y --query-timeout 10m --bash-tool-timeout 5m -p "{prompt}"',
        "not a permission grant from context-eval",
        "--allowed-tool",
        "agent x task x variant x trial",
        "--check-agents",
        "executable availability",
        "Existing configs with a single `agent` field remain valid",
        "unknown variables",
        "must not publish an absolute coding-agent ranking",
        "does not install Codex CLI",
    ]:
        assert term in text


def test_local_app_workflow_spec_documents_full_visual_workflow() -> None:
    text = Path("docs/local-app-workflow.md").read_text(encoding="utf-8")

    for heading in [
        "## User Contract",
        "## Modes",
        "## Installation And Startup",
        "## Project And Configuration Workflow",
        "## Evaluation Criteria Workflow",
        "## Preflight Workflow",
        "## Run Orchestration Workflow",
        "## Results Workflow",
        "## API Boundary",
        "## Non-Goals",
        "## Test Plan",
    ]:
        assert heading in text

    for term in [
        "non-technical user",
        "Static UI",
        "Local app mode",
        "context-eval app",
        "context-eval-app",
        "opens the browser automatically",
        "local app launcher log",
        "preflight",
        "validation commands",
        "run ID",
        "stdout/stderr log tails",
        "failed, timeout, low-confidence, and telemetry-gap cases",
        "GET /api/health",
        "POST /api/run-plan",
        "GET /api/exports",
        "loopback",
        "does not add a hosted service",
        "docs/designer-usability.md",
    ]:
        assert term in text


def test_designer_usability_spec_documents_planner_workflow() -> None:
    text = Path("docs/designer-usability.md").read_text(encoding="utf-8")

    for heading in [
        "## Product Purpose",
        "## User Scope",
        "## Terminology",
        "## UI Requirements",
        "## Acceptance Criteria",
    ]:
        assert heading in text

    for term in [
        "context package, not the agent brand",
        "测试用例",
        "上下文方案",
        "人工反馈",
        "`AGENTS.md`",
        "`skills`",
        "Agent 工作说明",
        "技能包",
        "local-only and artifact-based",
        "not a public benchmark",
        "not an agent leaderboard",
        "no automatic OpenAI, Claude, or other LLM judge",
        "validation passing means configured checks passed",
        "AI arbitration is optional soft evidence",
    ]:
        assert term in text


def test_openspec_change_contains_required_artifacts_and_capabilities() -> None:
    archive_dirs = sorted(Path("openspec/changes/archive").glob("*-agent-profiles-local-app"))
    assert archive_dirs
    change_dir = archive_dirs[-1]

    expected_files = [
        "proposal.md",
        "design.md",
        "tasks.md",
        "specs/agent-profiles/spec.md",
        "specs/local-app-workflow/spec.md",
    ]
    for relative in expected_files:
        assert (change_dir / relative).exists()

    proposal = (change_dir / "proposal.md").read_text(encoding="utf-8")
    for term in [
        "`agent-profiles`",
        "`local-app-workflow`",
        "Codex CLI",
        "Claude Code",
        "traecli",
        "`coco -p {prompt_file}`",
    ]:
        assert term in proposal


def test_openspec_specs_define_scenarios_for_agent_profiles_and_local_app() -> None:
    agent_spec = Path("openspec/specs/agent-profiles/spec.md").read_text(encoding="utf-8")
    app_spec = Path("openspec/specs/local-app-workflow/spec.md").read_text(encoding="utf-8")

    for term in [
        "Define local, noninteractive coding-agent profile configuration",
        "### Requirement: Named local agent profiles",
        "#### Scenario: Existing single-agent config remains valid",
        "### Requirement: Noninteractive command template contract",
        "#### Scenario: Custom agent command is supported",
        "#### Scenario: traecli command is supported",
        "#### Scenario: Optional executable check fails before execution",
        "### Requirement: Agent matrix execution",
        "agent x task x variant x trial",
    ]:
        assert term in agent_spec

    for term in [
        "Define the explicit loopback local app workflow",
        "### Requirement: Separate static UI and local app modes",
        "#### Scenario: Static UI remains offline",
        "### Requirement: Visual configuration workflow",
        "#### Scenario: Save reloads from disk",
        "#### Scenario: Safe task YAML editing is available",
        "### Requirement: Chinese local app experience",
        "### Requirement: Edited path safety",
        "### Requirement: Preflight before agent execution",
        "### Requirement: Visual run orchestration",
        "### Requirement: No-command-line product path",
        "#### Scenario: Packaged launcher starts the loopback app",
        "#### Scenario: Startup failures show diagnostics",
        "### Requirement: Harness readiness reference",
    ]:
        assert term in app_spec


def test_existing_docs_link_to_new_specs_without_claiming_implementation() -> None:
    readme = Path("README.md").read_text(encoding="utf-8")
    adapter = Path("docs/adapter-api.md").read_text(encoding="utf-8")
    local_ui = Path("docs/local-ui-config-editor.md").read_text(encoding="utf-8")
    configuration = Path("docs/configuration.md").read_text(encoding="utf-8")

    assert "docs/local-app-workflow.md" in readme
    assert "context-eval app --workspace" in readme
    assert "binds to loopback by default" in readme
    assert "docs/agent-profiles.md" in adapter
    assert "docs/agent-profiles.md" in configuration
    assert "docs/local-app-workflow.md" in local_ui
    assert "Static UI must stay safe" in local_ui
