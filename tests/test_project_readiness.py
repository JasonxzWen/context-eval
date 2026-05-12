import tomllib
from pathlib import Path

import yaml


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


def test_pytest_declares_local_e2e_marker_outside_default_matrix() -> None:
    pyproject = tomllib.loads(Path("pyproject.toml").read_text(encoding="utf-8"))
    pytest_options = pyproject["tool"]["pytest"]["ini_options"]

    assert pytest_options["addopts"] == '-m "not local_e2e"'
    assert any(
        marker.startswith("local_e2e: installed CLI smoke")
        for marker in pytest_options["markers"]
    )


def test_ci_exposes_dedicated_local_e2e_smoke_job() -> None:
    workflow = Path(".github/workflows/ci.yml").read_text(encoding="utf-8")

    assert "  local-e2e:" in workflow
    local_e2e_job = workflow.split("  local-e2e:", maxsplit=1)[1].split(
        "  skill-validation:",
        maxsplit=1,
    )[0]

    for term in [
        "name: Local E2E smoke",
        "runs-on: ubuntu-latest",
        'python-version: "3.12"',
        'python -m pip install -e ".[dev]"',
        "python -m pytest tests/test_local_e2e_smoke.py -m local_e2e",
    ]:
        assert term in local_e2e_job


def test_skill_validation_ci_job_installs_script_dependencies() -> None:
    workflow = Path(".github/workflows/ci.yml")
    text = workflow.read_text(encoding="utf-8")
    skill_job = text.split("  skill-validation:", maxsplit=1)[1]

    assert "actions/setup-python@v5" in skill_job
    assert 'python -m pip install -e ".[dev]"' in skill_job
    assert skill_job.index('python -m pip install -e ".[dev]"') < skill_job.index(
        "scripts\\validate-skills.ps1 -SkipExternal"
    )


def test_ci_runs_prepare_release_for_package_build() -> None:
    pyproject = Path("pyproject.toml").read_text(encoding="utf-8")
    workflow = Path(".github/workflows/ci.yml").read_text(encoding="utf-8")

    assert '"build>=1"' in pyproject
    assert "  package-build:" in workflow
    package_job = workflow.split("  package-build:", maxsplit=1)[1]

    assert 'python -m pip install "build>=1"' in package_job
    assert "python scripts/prepare-release.py --dist-dir dist" in package_job
    assert 'python -m pip install -e ".[dev]"' not in package_job


def test_ci_uses_single_release_preparation_entrypoint() -> None:
    workflow = Path(".github/workflows/ci.yml").read_text(encoding="utf-8")
    package_job = workflow.split("  package-build:", maxsplit=1)[1]

    assert "python scripts/check-release-state.py" not in package_job
    assert "python -m build" not in package_job
    assert "python scripts/inspect-package-artifacts.py dist" not in package_job


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


def test_release_checklist_documents_artifact_inspection_command() -> None:
    text = Path("docs/release-checklist.md").read_text(encoding="utf-8")

    for term in [
        "python scripts/inspect-package-artifacts.py C:\\tmp\\context-eval-dist",
        "inspects both the wheel and sdist artifacts",
        "requires `context_eval/`",
        "requires `context_eval/reports/templates/`",
        "rejects `.context-eval/`",
        "rejects `.agents/`",
        "rejects `.codex/skills/`",
        "rejects `openspec/`",
        "rejects `scripts/`",
    ]:
        assert term in text


def test_release_checklist_documents_prepare_release_boundaries() -> None:
    text = Path("docs/release-checklist.md").read_text(encoding="utf-8")

    for term in [
        "## Automated Preparation Command",
        "python scripts/prepare-release.py --dist-dir C:\\tmp\\context-eval-dist",
        "checks CHANGELOG.md",
        "runs the release-state check before package builds",
        "builds wheel and sdist artifacts",
        "inspects artifacts before publish",
        "does not create Git tags",
        "does not upload or publish packages",
        "manual publish checkpoint",
    ]:
        assert term in text


def test_release_checklist_documents_hidden_release_state_check() -> None:
    text = Path("docs/release-checklist.md").read_text(encoding="utf-8")

    for term in [
        "python scripts/check-release-state.py",
        "hidden local release blockers",
        "rejects `.context-eval/`",
        "rejects `build/`",
        "rejects `dist/`",
        "rejects `*.egg-info/`",
        "rejects `.codex/config.toml`",
        "allows `.venv/`",
        "allows cache directories",
        "allows Ralph local state",
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


def test_release_checklist_documents_python_platform_support_contract() -> None:
    text = Path("docs/release-checklist.md").read_text(encoding="utf-8")

    for term in [
        "## Supported Runtime And Platforms",
        "supports Python 3.11 or newer",
        "CI gates Python 3.11 and Python 3.12",
        "CI gates Ubuntu and Windows",
        "macOS is not a release-blocking CI platform yet",
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


def test_changelog_mentions_python_platform_support_docs() -> None:
    text = Path("CHANGELOG.md").read_text(encoding="utf-8")

    assert "Python and platform support" in text
    assert "release readiness" in text


def test_changelog_mentions_automated_package_artifact_inspection() -> None:
    text = Path("CHANGELOG.md").read_text(encoding="utf-8")

    assert "automated package artifact inspection" in text
    assert "wheel and sdist" in text


def test_changelog_mentions_release_state_checking() -> None:
    text = Path("CHANGELOG.md").read_text(encoding="utf-8")

    assert "release-state check" in text
    assert "hidden local release blockers" in text


def test_changelog_mentions_prepare_release_entrypoint() -> None:
    text = Path("CHANGELOG.md").read_text(encoding="utf-8")

    assert "release preparation entrypoint" in text
    assert "manual tag and publish checkpoint" in text


def test_pyproject_and_ci_matrix_match_supported_runtime_contract() -> None:
    pyproject = tomllib.loads(Path("pyproject.toml").read_text(encoding="utf-8"))
    workflow = yaml.safe_load(Path(".github/workflows/ci.yml").read_text(encoding="utf-8"))

    matrix = workflow["jobs"]["test"]["strategy"]["matrix"]

    assert pyproject["project"]["requires-python"] == ">=3.11"
    assert set(matrix["python-version"]) == {"3.11", "3.12"}
    assert set(matrix["os"]) == {"ubuntu-latest", "windows-latest"}


def test_readme_documents_supported_runtime_and_platform_limits() -> None:
    text = Path("README.md").read_text(encoding="utf-8")

    for term in [
        "Python 3.11 or newer is required",
        "CI currently gates Python 3.11 and Python 3.12",
        "CI currently gates Ubuntu and Windows",
        "Windows PowerShell is required for vendored skill validation",
    ]:
        assert term in text


def test_readme_documents_package_artifact_inspection_command() -> None:
    text = Path("README.md").read_text(encoding="utf-8")

    for term in [
        "python scripts/inspect-package-artifacts.py C:\\tmp\\context-eval-dist",
        "checks the built wheel and sdist",
        "runtime package scope",
    ]:
        assert term in text


def test_readme_documents_release_state_check_command() -> None:
    text = Path("README.md").read_text(encoding="utf-8")

    for term in [
        "python scripts/check-release-state.py",
        "hidden local release blockers",
        "before building package artifacts",
    ]:
        assert term in text


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


def test_readme_documents_prepare_release_entrypoint() -> None:
    text = Path("README.md").read_text(encoding="utf-8")

    for term in [
        "python scripts/prepare-release.py --dist-dir C:\\tmp\\context-eval-dist",
        "checks CHANGELOG.md",
        "runs the release-state check",
        "builds and inspects release artifacts",
        "does not tag or publish",
    ]:
        assert term in text


def test_readme_documents_optional_local_telemetry_workflow() -> None:
    text = Path("README.md").read_text(encoding="utf-8")

    for term in [
        "## Optional Local Agent Telemetry",
        "collector: \"json-file\"",
        "{telemetry_file}",
        "CONTEXT_EVAL_TELEMETRY_FILE",
        "agent_duration_seconds",
        "telemetry_status",
        "telemetry_source",
        "telemetry_error",
        "local artifacts only",
        "does not call hosted services",
    ]:
        assert term in text
