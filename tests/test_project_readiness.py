import tomllib
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


def test_ci_runs_package_build_with_dev_dependency() -> None:
    pyproject = Path("pyproject.toml").read_text(encoding="utf-8")
    workflow = Path(".github/workflows/ci.yml").read_text(encoding="utf-8")

    assert '"build>=1"' in pyproject
    assert "  package-build:" in workflow
    package_job = workflow.split("  package-build:", maxsplit=1)[1]

    assert 'python -m pip install -e ".[dev]"' in package_job
    assert "python -m build" in package_job
    assert package_job.index('python -m pip install -e ".[dev]"') < package_job.index(
        "python -m build"
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


def test_release_checklist_documents_package_build_scope() -> None:
    text = Path("docs/release-checklist.md").read_text(encoding="utf-8")

    for term in [
        "python -m build --outdir",
        "Inspect both the wheel and sdist",
        "includes `context_eval/`",
        "includes `context_eval/reports/templates/`",
        "do not include `.context-eval/`",
        "do not include `.agents/`",
        "do not include `.codex/skills/`",
        "do not include `openspec/`",
        "do not include `scripts/`",
    ]:
        assert term in text


def test_release_checklist_documents_spdx_license_metadata_contract() -> None:
    text = Path("docs/release-checklist.md").read_text(encoding="utf-8")

    for term in [
        "Package metadata must use `project.license` as an SPDX string",
        "`license = \"MIT\"`",
        "must not use table-form license metadata",
        "`license = { text = \"MIT\" }`",
        "does not change the runtime package scope",
    ]:
        assert term in text


def test_pyproject_uses_spdx_license_string_metadata() -> None:
    pyproject = tomllib.loads(Path("pyproject.toml").read_text(encoding="utf-8"))
    license_metadata = pyproject["project"]["license"]

    assert license_metadata == "MIT"
    assert not isinstance(license_metadata, dict)


def test_changelog_mentions_spdx_license_metadata_cleanup() -> None:
    text = Path("CHANGELOG.md").read_text(encoding="utf-8")

    assert "SPDX license metadata" in text
    assert "table-form license metadata" in text


def test_readme_documents_local_package_build_verification() -> None:
    text = Path("README.md").read_text(encoding="utf-8")

    for term in [
        "## Development Verification",
        "python -m build --outdir",
        "docs/release-checklist.md",
        "`context_eval/` is the runtime package",
        "maintainer capability library",
        "not runtime package modules",
    ]:
        assert term in text
