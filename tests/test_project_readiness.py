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
    assert "context-eval validate-config --config examples/agent-matrix/context-eval.yaml" in text
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
    for dependency in [
        '"typer>=0.12"',
        '"pydantic>=2"',
        '"PyYAML>=6"',
        '"rich>=13"',
        '"Jinja2>=3"',
    ]:
        assert dependency in package_job
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


def test_release_version_metadata_matches_changelog() -> None:
    pyproject = tomllib.loads(Path("pyproject.toml").read_text(encoding="utf-8"))
    init_text = Path("context_eval/__init__.py").read_text(encoding="utf-8")
    changelog_text = Path("CHANGELOG.md").read_text(encoding="utf-8")

    assert pyproject["project"]["version"] == "0.1.3"
    assert '__version__ = "0.1.3"' in init_text
    assert "## v0.1.3 - 2026-05-15" in changelog_text


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


def test_release_checklist_documents_release_candidate_install_smoke() -> None:
    text = Path("docs/release-checklist.md").read_text(encoding="utf-8")

    for term in [
        "## Release Candidate Install Smoke",
        "python scripts/install-smoke-artifacts.py --dist-dir C:\\tmp\\context-eval-dist",
        "installs the built wheel",
        "installed `context-eval-app` launcher",
        "context-eval-app --workspace",
        "--no-browser --port 0 --check-startup",
        "temporary Python environment",
        "local fixture repository",
        "fake local agent",
        "does not call hosted services",
        "does not create Git tags",
        "does not upload or publish packages",
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


def test_changelog_mentions_release_candidate_install_smoke() -> None:
    text = Path("CHANGELOG.md").read_text(encoding="utf-8")

    assert "release candidate install smoke" in text
    assert "built package artifacts" in text


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


def test_readme_documents_packaged_local_app_launcher() -> None:
    text = Path("README.md").read_text(encoding="utf-8")

    for term in [
        "context-eval-app",
        "--check-startup",
        "opens the browser automatically",
        "local app launcher log",
        "does not install coding agents",
        "does not create tags or publish packages",
    ]:
        assert term in text


def test_local_app_workflow_documents_launcher_install_start_recovery() -> None:
    text = Path("docs/local-app-workflow.md").read_text(encoding="utf-8")

    for term in [
        "## Launcher Packaging",
        "`context-eval-app`",
        "`--check-startup`",
        "shortcut target",
        "startup diagnostics",
        "local app launcher log",
        "Recovery",
        "does not install external coding agents",
        "manual tag and publish boundary",
    ]:
        assert term in text


def test_readme_documents_release_candidate_install_smoke() -> None:
    text = Path("README.md").read_text(encoding="utf-8")

    for term in [
        "release candidate install smoke",
        "python scripts/install-smoke-artifacts.py --dist-dir C:\\tmp\\context-eval-dist",
        "built wheel",
        "installed `context-eval-app` launcher",
        "--no-browser --port 0 --check-startup",
        "temporary Python environment",
        "fixture repository",
        "fake local agent",
        "does not call hosted services",
    ]:
        assert term in text


def test_readme_documents_windows_portable_launcher_package() -> None:
    text = Path("README.md").read_text(encoding="utf-8")

    for term in [
        "Windows portable package",
        "context-eval-windows-x64-<version>.zip",
        "Start Context Eval.cmd",
        "scripts/build-windows-portable.py",
        "--frontend-dist frontend\\dist",
        "private `.venv`",
        "does not install coding agents",
        "does not install target repository dependencies",
    ]:
        assert term in text


def test_release_checklist_documents_windows_portable_launcher_package() -> None:
    text = Path("docs/release-checklist.md").read_text(encoding="utf-8")

    for term in [
        "## Windows Portable Package",
        "python scripts/build-windows-portable.py",
        "--dist-dir C:\\tmp\\context-eval-dist",
        "--frontend-dist frontend\\dist",
        "context-eval-windows-x64-<version>.zip",
        "Start Context Eval.cmd",
        "Python 3.11 or newer",
        "manual tag and publish checkpoint",
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


def test_readme_documents_agent_profile_matrix_example() -> None:
    text = Path("README.md").read_text(encoding="utf-8")

    for term in [
        "## Agent Profile Matrix Example",
        "examples/agent-matrix/context-eval.yaml",
        "codex-cli",
        "claude-code",
        "traecli",
        'coco -y --query-timeout 10m --bash-tool-timeout 5m -p "{prompt}"',
        "not a permission grant from context-eval",
        "--allowed-tool",
        "context-eval run --config examples/agent-matrix/context-eval.yaml --dry-run --agent trae",
        "local observations",
        "not an absolute agent leaderboard",
    ]:
        assert term in text


def test_readme_documents_agent_executable_preflight() -> None:
    text = Path("README.md").read_text(encoding="utf-8")

    for term in [
        "context-eval validate-config --strict --check-agents",
        "checks configured command executables",
        "does not run agent commands",
        "does not install coding agents",
    ]:
        assert term in text


def test_local_app_harness_readiness_documents_skill_hub_reference() -> None:
    text = Path("docs/local-app-harness-readiness.md").read_text(encoding="utf-8")

    for term in [
        "https://github.com/JasonxzWen/skill-hub",
        "42c3065378e1d1d2851ca0e387e915a2841b885e",
        "`build`",
        "`test`",
        "`validate`",
        "`validate:release`",
        "html-work-reports",
        "self-contained static HTML reports",
        "source-linked file evidence",
        "degraded browser coverage",
        "python scripts\\validate-frontend.py --install --install-browsers",
        "read-only",
        "category-based",
        "scoreless",
        "maintainer tooling only",
        "should not add a scoring model",
        "automatic target-repository commit workflow",
    ]:
        assert term in text


def test_skill_hub_import_documents_refreshed_minimal_profile_skills() -> None:
    text = Path("docs/skill-hub-import.md").read_text(encoding="utf-8")

    for term in [
        "Latest refreshed commit: `42c3065378e1d1d2851ca0e387e915a2841b885e`",
        "Latest refresh date: `2026-05-14`",
        "`html-work-reports`",
        "`compound-code-review`",
        "`diagnose`",
        "`prototype`",
        "`grill-me`",
        "does not import `feynman-learning-coach`",
        "not needed for this project's runtime package",
    ]:
        assert term in text


def test_html_work_reports_skill_assets_are_installed() -> None:
    root = Path(".agents/skills/html-work-reports")

    for skill_name in [
        "compound-code-review",
        "diagnose",
        "grill-me",
        "html-work-reports",
        "prototype",
    ]:
        skill_root = Path(".agents/skills") / skill_name
        assert (skill_root / "SKILL.md").exists()
        assert (skill_root / "agents/openai.yaml").exists()

    for relative in [
        "SKILL.md",
        "agents/openai.yaml",
        "scripts/create-report.mjs",
        "scripts/validate-html-report.mjs",
        "references/report-input-schema.json",
        "references/html-report-patterns.md",
        "assets/components/report-ui.css",
        "assets/components/report-ui.js",
        "assets/templates/implementation-handoff.html",
        "assets/templates/review-findings.html",
    ]:
        assert (root / relative).exists()

    skill = (root / "SKILL.md").read_text(encoding="utf-8")
    assert "self-contained static `.html`" in skill
    assert "source file link" in skill
    assert "scripts/validate-html-report.mjs" in skill
