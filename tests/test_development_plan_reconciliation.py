from pathlib import Path


def _section(text: str, heading: str, next_heading: str | None = None) -> str:
    start = text.index(heading)
    end = text.index(next_heading, start) if next_heading is not None else len(text)
    return text[start:end]


def _epic_sections(text: str) -> list[str]:
    headings = [
        "## Capability Epic A:",
        "## Capability Epic B:",
        "## Capability Epic C:",
        "## Capability Epic D:",
        "## Capability Epic E:",
        "## Capability Epic F:",
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


def test_development_plan_uses_seven_larger_capability_epics() -> None:
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
    ]
    for heading in expected_headings:
        assert heading in text

    assert text.count("## Capability Epic ") == 7
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
        "replace the fine-grained active backlog with seven capability epics",
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
