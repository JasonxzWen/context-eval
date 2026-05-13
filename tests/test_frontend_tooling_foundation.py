import json
import tomllib
from pathlib import Path

import yaml


def test_frontend_tooling_openspec_artifacts_exist_and_define_scope() -> None:
    change_dir = Path("openspec/changes/frontend-tooling-foundation")

    for relative in [
        "proposal.md",
        "design.md",
        "tasks.md",
        "specs/frontend-tooling/spec.md",
    ]:
        assert (change_dir / relative).exists()

    proposal = (change_dir / "proposal.md").read_text(encoding="utf-8")
    spec = (change_dir / "specs/frontend-tooling/spec.md").read_text(encoding="utf-8")

    for term in [
        "`frontend-tooling`",
        "development-only Node/npm tooling",
        "Do not implement the local app server",
    ]:
        assert term in proposal

    for term in [
        "### Requirement: Frontend package quality gate",
        "#### Scenario: Frontend validation runs all local app UI gates",
        "### Requirement: Browser acceptance foundation",
        "#### Scenario: Built frontend passes desktop and narrow smoke checks",
        "### Requirement: CI exposes frontend validation",
    ]:
        assert term in spec


def test_development_plan_inserts_frontend_foundation_before_local_app_server() -> None:
    text = Path("docs/development-plan.md").read_text(encoding="utf-8")

    frontend_heading = "## Capability Epic I: Frontend Build/Test/Acceptance Foundation"
    server_heading = "## Capability Epic J: Local App Server And Run Orchestration"
    ui_heading = "## Capability Epic K: Full Web UI Workflow For Non-Technical Users"

    assert frontend_heading in text
    assert server_heading in text
    assert ui_heading in text
    assert text.index(frontend_heading) < text.index(server_heading) < text.index(ui_heading)

    for term in [
        "React + Vite + TypeScript",
        "Vitest",
        "Playwright",
        "scripts\\validate-frontend.py --install --install-browsers",
        "does not add local app server endpoints",
    ]:
        assert term in text


def test_frontend_workflow_doc_defines_build_test_acceptance_commands() -> None:
    text = Path("docs/frontend-workflow.md").read_text(encoding="utf-8")

    for heading in [
        "## Scope",
        "## Toolchain",
        "## Commands",
        "## Browser Acceptance",
        "## Build Output",
        "## CI",
        "## Non-Goals",
    ]:
        assert heading in text

    for term in [
        "npm run typecheck",
        "npm run test",
        "npm run build",
        "npm run e2e",
        "npm run validate",
        "python scripts\\validate-frontend.py --install --install-browsers",
        "frontend/dist",
        "loopback local app API",
        "fixture fallback",
        "does not make Node or npm a runtime requirement",
    ]:
        assert term in text


def test_readme_and_local_app_docs_link_frontend_workflow() -> None:
    readme = Path("README.md").read_text(encoding="utf-8")
    local_app = Path("docs/local-app-workflow.md").read_text(encoding="utf-8")

    for text in [readme, local_app]:
        assert "docs/frontend-workflow.md" in text
        assert "scripts\\validate-frontend.py --install --install-browsers" in text


def test_frontend_package_scripts_match_validation_contract() -> None:
    package = json.loads(Path("frontend/package.json").read_text(encoding="utf-8"))
    scripts = package["scripts"]

    assert package["private"] is True
    assert package["type"] == "module"
    assert scripts["typecheck"] == "tsc --noEmit"
    assert scripts["test"] == "vitest run"
    assert scripts["build"] == "vite build"
    assert scripts["e2e"] == "playwright test"
    assert scripts["validate"] == (
        "npm run typecheck && npm run test && npm run build && npm run e2e"
    )

    for dependency in ["@vitejs/plugin-react", "vite", "typescript", "vitest", "@playwright/test"]:
        assert dependency in package["devDependencies"]

    for dependency in ["react", "react-dom"]:
        assert dependency in package["dependencies"]


def test_root_frontend_validation_wrapper_is_script_friendly() -> None:
    script = Path("scripts/validate-frontend.py").read_text(encoding="utf-8")

    for term in [
        "npm ci",
        "npm run validate",
        "CONTEXT_EVAL_PYTHON",
        "--install",
        "--install-browsers",
        "--install-system-deps",
        "frontend",
    ]:
        assert term in script


def test_ci_exposes_dedicated_frontend_validation_job() -> None:
    workflow = yaml.safe_load(Path(".github/workflows/ci.yml").read_text(encoding="utf-8"))
    jobs = workflow["jobs"]

    assert "frontend-validation" in jobs
    job = jobs["frontend-validation"]

    assert job["name"] == "Frontend validation"
    assert job["runs-on"] == "ubuntu-latest"

    steps_text = "\n".join(str(step) for step in job["steps"])
    for term in [
        "actions/setup-node@v4",
        "node-version-file",
        "python -m pip install -e \".[dev]\"",
        "python scripts/validate-frontend.py --install --install-browsers --install-system-deps",
    ]:
        assert term in steps_text


def test_frontend_outputs_and_runtime_package_boundary_are_explicit() -> None:
    gitignore = Path(".gitignore").read_text(encoding="utf-8")
    pyproject = tomllib.loads(Path("pyproject.toml").read_text(encoding="utf-8"))
    vite_config = Path("frontend/vite.config.ts").read_text(encoding="utf-8")

    for ignored_path in [
        "frontend/node_modules/",
        "frontend/dist/",
        "frontend/playwright-report/",
        "frontend/test-results/",
        "frontend/coverage/",
    ]:
        assert ignored_path in gitignore

    package_data = pyproject["tool"]["setuptools"]["package-data"]["context_eval"]
    assert all("frontend" not in entry for entry in package_data)
    assert "outDir: 'dist'" in vite_config
