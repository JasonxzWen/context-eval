from pathlib import Path


def test_agent_telemetry_spec_defines_collector_contract() -> None:
    spec = Path("docs/agent-telemetry.md")
    assert spec.exists()

    text = spec.read_text(encoding="utf-8")
    required_sections = [
        "## User Contract",
        "## Metric Classes",
        "## Hook And Collector Model",
        "## Result Schema",
        "## Reporting Behavior",
        "## Non-Goals",
        "## Test Plan",
    ]
    for section in required_sections:
        assert section in text

    required_terms = [
        "runner-guaranteed",
        "hook-provided",
        "telemetry_status",
        "telemetry_source",
        "prompt_tokens",
        "completion_tokens",
        "total_tokens",
        "reasoning_tokens",
        "tool_call_count",
        "tool_calls_by_name",
        "no-op collector",
        "generic JSON telemetry collector",
        "context-eval evaluates the effect of context variants",
    ]
    for term in required_terms:
        assert term in text


def test_development_plan_includes_agent_telemetry_phase() -> None:
    plan = Path("docs/development-plan.md").read_text(encoding="utf-8")

    assert "## Phase 4.5: Agent Telemetry And Usage Accounting" in plan
    assert "docs/agent-telemetry.md" in plan
    assert "runner-guaranteed" in plan
    assert "hook-provided" in plan
    assert "generic JSON telemetry collector" in plan
    assert "Do not claim absolute coding-agent capability" in plan
    assert "Agent telemetry contract and normalized result schema" in plan


def test_evaluation_docs_describe_normalized_telemetry_fields() -> None:
    text = Path("docs/evaluation.md").read_text(encoding="utf-8")

    required_terms = [
        "## Normalized Telemetry Fields",
        "telemetry_status",
        "telemetry_source",
        "telemetry_error",
        "agent_duration_seconds",
        "prompt_tokens",
        "completion_tokens",
        "total_tokens",
        "reasoning_tokens",
        "tool_call_count",
        "tool_calls_by_name",
        "Old `results.jsonl` rows",
    ]
    for term in required_terms:
        assert term in text
