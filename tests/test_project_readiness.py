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


def test_skill_validation_ci_job_installs_script_dependencies() -> None:
    workflow = Path(".github/workflows/ci.yml")
    text = workflow.read_text(encoding="utf-8")
    skill_job = text.split("  skill-validation:", maxsplit=1)[1]

    assert "actions/setup-python@v5" in skill_job
    assert 'python -m pip install -e ".[dev]"' in skill_job
    assert skill_job.index('python -m pip install -e ".[dev]"') < skill_job.index(
        "scripts\\validate-skills.ps1 -SkipExternal"
    )


def test_skill_validation_skip_external_does_not_require_home_tools() -> None:
    script = Path("scripts/validate-skills.ps1").read_text(encoding="utf-8")

    assert "[string]$QuickValidatePath" in script
    assert "-not $SkipExternal" in script
    assert "Skipping quick_validate.py" in script


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
