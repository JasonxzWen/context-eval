from pathlib import Path


def test_config_diagnostics_spec_documents_contract() -> None:
    spec = Path("docs/config-diagnostics.md")
    assert spec.exists()

    text = spec.read_text(encoding="utf-8")

    for heading in [
        "## User Contract",
        "## Error Taxonomy",
        "## Diagnostic Context",
        "## Strict Validation",
        "## Non-Goals",
        "## Test Plan",
    ]:
        assert heading in text

    for term in [
        "field-specific",
        "YAML parse error",
        "schema validation",
        "missing file",
        "unsafe path",
        "duplicate task id",
        "Git ref",
        "side-effect-free",
        "no workspace",
        "no agent run",
        "no validation command",
        "no network call",
        "repo.path",
        "agent.prompt_template",
        "variant",
        "overlay",
        "task id",
        "task.repo_ref",
    ]:
        assert term in text


def test_development_plan_links_config_diagnostics_spec() -> None:
    text = Path("docs/development-plan.md").read_text(encoding="utf-8")

    assert "docs/config-diagnostics.md" in text
