from pathlib import Path


def test_multi_agent_comparison_spec_defines_contract() -> None:
    spec = Path("docs/multi-agent-comparison.md").read_text(encoding="utf-8")

    for heading in [
        "## User Contract",
        "## Source Artifacts",
        "## Comparison Dimensions",
        "## Export Formats",
        "## Reporting Behavior",
        "## Static UI Behavior",
        "## Non-Goals",
        "## Test Plan",
    ]:
        assert heading in spec

    for term in [
        "results.jsonl",
        "run_metadata.json",
        "agent_name",
        "task_id",
        "variant",
        "trial_index",
        "status",
        "validation_status",
        "confidence",
        "duration_seconds",
        "agent_duration_seconds",
        "prompt_tokens",
        "completion_tokens",
        "total_tokens",
        "reasoning_tokens",
        "tool_call_count",
        "tool_calls_by_name",
        "deterministic",
        "CSV",
        "compact JSON",
    ]:
        assert term in spec


def test_multi_agent_comparison_spec_documents_non_goals() -> None:
    spec = Path("docs/multi-agent-comparison.md").read_text(encoding="utf-8")

    for non_goal in [
        "LLM judge",
        "hosted dashboard",
        "multi-user web",
        "automatic coding-agent installation",
        "real network isolation",
        "absolute agent capability ranking",
    ]:
        assert non_goal in spec


def test_development_plan_links_multi_agent_comparison_spec() -> None:
    plan = Path("docs/development-plan.md").read_text(encoding="utf-8")

    assert "docs/multi-agent-comparison.md" in plan
    assert "CSV and compact JSON" in plan
    assert "not an absolute" in plan
