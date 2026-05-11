from pathlib import Path


def _section(text: str, heading: str, next_heading: str | None = None) -> str:
    start = text.index(heading)
    end = text.index(next_heading, start) if next_heading is not None else len(text)
    return text[start:end]


def _squash(text: str) -> str:
    return " ".join(text.split())


def test_development_plan_defines_reconciliation_status_model() -> None:
    text = Path("docs/development-plan.md").read_text(encoding="utf-8")

    for term in [
        "## Plan Status Model",
        "`complete for current scope`",
        "`mostly complete`",
        "`planned next`",
        "`deferred`",
        "A status line must separate shipped behavior from remaining backlog",
    ]:
        assert term in text


def test_development_plan_reconciles_merged_phase_statuses() -> None:
    text = Path("docs/development-plan.md").read_text(encoding="utf-8")

    expected_statuses = {
        "## Phase 1: Core Runner Correctness": (
            "Status: complete for current scope."
        ),
        "## Phase 2: Configuration And Task Spec Maturity": (
            "Status: mostly complete; validation command timeout defaults remain."
        ),
        "## Phase 3: User Workflow Usability": (
            "Status: complete for current scope."
        ),
        "## Phase 4: Execution Control And Reproducibility": (
            "Status: complete for current scope."
        ),
        "## Phase 4.5: Agent Telemetry And Usage Accounting": (
            "Status: complete for first collector scope; agent-specific collectors "
            "are deferred."
        ),
        "## Phase 5: Reporting And Analysis": (
            "Status: complete for artifact-based reporting; UI save/server mode "
            "and report polish remain."
        ),
        "## Phase 6: Adapter And Prompt Extensibility": (
            "Status: complete for prompt-template scope; thin Python entrypoint "
            "adapter is deferred."
        ),
        "## Phase 7: CI And Release Readiness": (
            "Status: complete for current release readiness; release automation "
            "remains."
        ),
    }

    for heading, status in expected_statuses.items():
        section = _squash(_section(text, heading))
        assert status in section


def test_development_plan_active_backlog_excludes_merged_work() -> None:
    text = Path("docs/development-plan.md").read_text(encoding="utf-8")
    backlog = _section(text, "## Active Backlog Order")

    for term in [
        "Validation command timeout defaults",
        "Config diagnostics and strict validation edge cases",
        "Local UI explicit save or server mode",
        "Agent-specific telemetry collectors",
        "Thin Python entrypoint adapter",
        "Report template readability",
        "Release automation",
        "Optional macOS release gate",
    ]:
        assert term in backlog

    for completed_term in [
        "Unique run directory guard",
        "Strict config validation and task filters",
        "Self-contained fixture repo example",
        "`context-eval run --dry-run`",
        "`context-eval init`",
        "Trial support",
        "Report/inspect commands",
        "CI workflow and release checklist",
    ]:
        assert completed_term not in backlog


def test_changelog_mentions_development_plan_reconciliation_handoff() -> None:
    text = Path("CHANGELOG.md").read_text(encoding="utf-8")

    for term in [
        "development plan status reconciliation",
        "active backlog handoff",
        "validation command timeout defaults",
    ]:
        assert term in text
