from pathlib import Path


def test_ci_workflow_contains_required_quality_gates() -> None:
    workflow = Path(".github/workflows/ci.yml")
    assert workflow.exists()

    text = workflow.read_text(encoding="utf-8")
    assert "python -m pytest" in text
    assert "ruff check" in text
    assert "context-eval validate-config --config examples/basic/context-eval.yaml" in text
    assert "scripts\\validate-skills.ps1 -SkipExternal" in text
    assert "3.11" in text
    assert "windows-latest" in text


def test_release_checklist_and_changelog_exist() -> None:
    checklist = Path("docs/release-checklist.md")
    changelog = Path("CHANGELOG.md")

    assert checklist.exists()
    assert changelog.exists()

    checklist_text = checklist.read_text(encoding="utf-8")
    assert "python -m pytest" in checklist_text
    expected_validate = "context-eval validate-config --config examples/basic/context-eval.yaml"
    assert expected_validate in checklist_text
    assert "scripts\\validate-skills.ps1 -SkipExternal" in checklist_text
    assert "context_eval" in checklist_text
    assert ".context-eval" in checklist_text

    changelog_text = changelog.read_text(encoding="utf-8")
    assert "## Unreleased" in changelog_text
