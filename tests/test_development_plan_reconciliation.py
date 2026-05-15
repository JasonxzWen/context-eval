from pathlib import Path


def _section(text: str, heading: str, next_heading: str | None = None) -> str:
    start = text.index(heading)
    end = text.index(next_heading, start) if next_heading is not None else len(text)
    return text[start:end]


def _epic_sections(text: str) -> list[str]:
    headings = [
        line
        for line in text.splitlines()
        if line.startswith("## Capability Epic ")
    ]
    return [
        _section(
            text,
            heading,
            headings[index + 1] if index + 1 < len(headings) else None,
        )
        for index, heading in enumerate(headings)
    ]


def test_development_plan_defines_capability_pr_cadence() -> None:
    text = Path("docs/development-plan.md").read_text(encoding="utf-8")

    for term in [
        "## Development Cadence Policy",
        "A Ralph story is not a pull request",
        "A capability PR should contain 3-6 related Ralph stories",
        "Each story still follows SDD + TDD",
        "Do not open one PR per story",
        "spec, tests, implementation, docs, verification",
    ]:
        assert term in text


def test_development_plan_audits_pr_1_to_17_and_batches_future_work() -> None:
    text = Path("docs/development-plan.md").read_text(encoding="utf-8")

    for term in [
        "## Capability Audit: PR #1-#17",
        "PR #1-#4 established broad capability slices",
        "PR #5-#17 delivered useful work, but the cadence became too fine-grained",
        (
            "release readiness was split across build, license, platform, "
            "artifact inspection, and release-state PRs"
        ),
        "Future planning should batch related stories into coherent capability PRs",
    ]:
        assert term in text


def test_development_plan_uses_larger_capability_epics() -> None:
    text = Path("docs/development-plan.md").read_text(encoding="utf-8")

    expected_headings = [
        "## Capability Epic A: Config Diagnostics And Strict Validation Hardening",
        "## Capability Epic B: Local UI Persistence And Server-Mode Decision",
        (
            "## Capability Epic C: Reporting Polish For Multi-Task, "
            "Multi-Variant, Multi-Agent Runs"
        ),
        "## Capability Epic D: Release Automation And Packaging Workflow Polish",
        "## Capability Epic E: Optional Adapter And Telemetry Expansion",
        "## Capability Epic F: Local E2E CI Smoke And Test Taxonomy",
        "## Capability Epic G: Release Candidate Install Smoke And Changelog Finalization",
        "## Capability Epic H: Agent Profiles And Noninteractive Agent Matrix",
        "## Capability Epic I: Frontend Build/Test/Acceptance Foundation",
        "## Capability Epic J: Local App Server And Run Orchestration",
        "## Capability Epic K: Full Web UI Workflow For Non-Technical Users",
        "## Capability Epic L: No-CLI Launcher And Packaging",
    ]
    for heading in expected_headings:
        assert heading in text

    assert text.count("## Capability Epic ") == 12
    assert "## Active Backlog Order" not in text
    assert "## Phase 7:" not in text


def test_each_capability_epic_has_merge_package_and_batching_rationale() -> None:
    text = Path("docs/development-plan.md").read_text(encoding="utf-8")

    required_subheads = [
        "### Goal",
        "### Scope",
        "### Non-Goals",
        "### Merge Acceptance Criteria",
        "### Suggested Ralph Stories",
        "### Test Strategy",
        "### Why One Capability PR",
    ]
    for section in _epic_sections(text):
        for subhead in required_subheads:
            assert subhead in section
        for term in [
            "spec",
            "tests",
            "implementation",
            "docs",
            "verification",
        ]:
            assert term in section


def test_changelog_mentions_larger_capability_pr_replanning() -> None:
    text = Path("CHANGELOG.md").read_text(encoding="utf-8")

    for term in [
        "Replan the development roadmap around larger capability PRs",
        "Ralph stories remain SDD/TDD units inside a capability PR",
        "replace the fine-grained active backlog with capability epics",
    ]:
        assert term in text


def test_development_plan_inserts_local_e2e_before_later_capability_work() -> None:
    text = Path("docs/development-plan.md").read_text(encoding="utf-8")
    epic_f = _section(
        text,
        "## Capability Epic F: Local E2E CI Smoke And Test Taxonomy",
        "## Capability Epic G: Release Candidate Install Smoke And Changelog Finalization",
    )

    for term in [
        "docs/local-e2e-ci.md",
        "local-e2e smoke",
        "installed CLI",
        "fixture repository",
        "context-eval run",
        "context-eval report",
        "context-eval export",
        "context-eval ui",
        "no hosted services",
        "no real external coding agent",
    ]:
        assert term in epic_f


def test_development_plan_prioritizes_agent_profiles_before_full_web_ui() -> None:
    text = Path("docs/development-plan.md").read_text(encoding="utf-8")

    required_order = [
        "PR H: Agent Profiles And Noninteractive Agent Matrix",
        "PR I: Frontend Build/Test/Acceptance Foundation",
        "PR J: Local App Server And Run Orchestration",
        "PR K: Full Web UI Workflow For Non-Technical Users",
        "PR L: No-CLI Launcher And Packaging",
    ]
    positions = [text.index(term) for term in required_order]
    assert positions == sorted(positions)

    epic_h = _section(
        text,
        "## Capability Epic H: Agent Profiles And Noninteractive Agent Matrix",
        "## Capability Epic I: Frontend Build/Test/Acceptance Foundation",
    )
    for term in [
        "Codex CLI",
        "Claude Code",
        "traecli",
        "Coco",
        "custom local commands",
        '`coco -y --query-timeout 10m --bash-tool-timeout 5m -p "{prompt}"`',
        '`traecli -p "{prompt}"`',
        "agent x task x variant x trial",
        "Existing single-agent configs continue to work unchanged",
        "Do not install Codex CLI",
    ]:
        assert term in epic_h


def test_development_plan_defines_local_app_and_no_cli_followups() -> None:
    text = Path("docs/development-plan.md").read_text(encoding="utf-8")
    epic_i = _section(
        text,
        "## Capability Epic I: Frontend Build/Test/Acceptance Foundation",
        "## Capability Epic J: Local App Server And Run Orchestration",
    )
    epic_j = _section(
        text,
        "## Capability Epic J: Local App Server And Run Orchestration",
        "## Capability Epic K: Full Web UI Workflow For Non-Technical Users",
    )
    epic_k = _section(
        text,
        "## Capability Epic K: Full Web UI Workflow For Non-Technical Users",
        "## Capability Epic L: No-CLI Launcher And Packaging",
    )
    epic_l = _section(
        text,
        "## Capability Epic L: No-CLI Launcher And Packaging",
        "## Cross-Epic Quality Gates",
    )

    for term in [
        "React + Vite + TypeScript",
        "Vitest",
        "Playwright",
        "frontend/dist",
        "does not add local app server endpoints",
    ]:
        assert term in epic_i

    for term in [
        "explicit local app/server command",
        "loopback",
        "config save/load",
        "preflight",
        "run lifecycle",
        "log streaming",
        "static UI mode",
    ]:
        assert term in epic_j

    for term in [
        "non-technical users",
        "first-run setup",
        "Chinese",
        "save-reload proof",
        "evaluation criteria",
        "run progress",
        "preserves unknown fields",
        "risk signals",
        "Browser verification",
    ]:
        assert term in epic_k

    for term in [
        "without requiring users to type a command",
        "starts the local app server and opens the browser",
        "Startup failures are visible",
        "Do not package external coding agents",
    ]:
        assert term in epic_l


def test_changelog_mentions_agent_profiles_and_local_app_specs() -> None:
    text = Path("CHANGELOG.md").read_text(encoding="utf-8")

    for term in [
        "agent profiles",
        "noninteractive",
        "local app/server mode",
        "full Web UI workflows",
        "no-command-line launcher",
    ]:
        assert term in text
