from pathlib import Path

import yaml

DOCS = Path("docs")


def test_readme_has_product_onboarding_sections() -> None:
    text = Path("README.md").read_text(encoding="utf-8")

    for heading in [
        "## What context-eval is",
        "## What problem it solves",
        "## What it compares",
        "## Minimal workflow",
        "## Demo and project documentation",
        "## What it is not",
        "## Quickstart",
    ]:
        assert heading in text

    for term in [
        "local Context A/B Testing Framework",
        "context variant",
        "Validation commands and human review",
        "docs/demo-workflow.md",
        "docs/index.md",
        "Not an agent leaderboard",
        "Not a hosted dashboard",
    ]:
        assert term in text


def test_project_documentation_site_pages_exist_and_are_linked() -> None:
    expected_pages = [
        "index.md",
        "demo-workflow.md",
        "architecture.md",
        "evaluation-methodology.md",
        "artifact-model.md",
        "faq.md",
        "pages-setup.md",
    ]

    for page in expected_pages:
        assert (DOCS / page).exists()

    index = (DOCS / "index.md").read_text(encoding="utf-8")
    for link in [
        "https://github.com/JasonxzWen/context-eval#quickstart",
        "demo-workflow.md",
        "architecture.md",
        "evaluation-methodology.md",
        "artifact-model.md",
        "faq.md",
        "frontend-workflow.md",
        "local-app-workflow.md",
        "agent-profiles.md",
        "development-plan.md",
        "release-checklist.md",
        "pages-setup.md",
    ]:
        assert link in index


def test_new_project_docs_preserve_local_observation_boundaries() -> None:
    docs_text = "\n".join(
        (DOCS / page).read_text(encoding="utf-8")
        for page in [
            "index.md",
            "demo-workflow.md",
            "architecture.md",
            "evaluation-methodology.md",
            "artifact-model.md",
            "faq.md",
        ]
    )

    for term in [
        "local observations",
        "context variant",
        "validation confidence",
        "artifact-only",
        "not absolute",
        "Validation commands",
        "human review",
        "static UI",
        "loopback",
        "does not install coding agents",
        "hosted services",
        "results.jsonl",
        "run_manifest.json",
    ]:
        assert term in docs_text


def test_architecture_and_methodology_docs_cover_core_contracts() -> None:
    architecture = (DOCS / "architecture.md").read_text(encoding="utf-8")
    methodology = (DOCS / "evaluation-methodology.md").read_text(encoding="utf-8")
    artifact_model = (DOCS / "artifact-model.md").read_text(encoding="utf-8")

    for term in [
        "config plus tasks",
        "run planning",
        "isolated workspace",
        "context overlays",
        "prompt rendering",
        "command-template agent execution",
        "validation commands",
        "diff, patch, logs, telemetry capture",
        "Runtime Package Boundary",
        "Artifact-Only Reporting",
    ]:
        assert term in architecture

    for term in [
        "context assets, not absolute agent intelligence",
        "Controlled Variables",
        "Experimental Variable",
        "Validation Defines Confidence",
        "No-Validation Cases",
        "Repeated Trials",
        "Why No LLM Judge As Truth",
    ]:
        assert term in methodology

    for term in [
        "results.jsonl",
        "run_metadata.json",
        "run_manifest.json",
        "report.md",
        "config_hash",
        "task_hash",
        "variant_hash",
        "schema_version",
        "Missing telemetry is explicit",
    ]:
        assert term in artifact_model


def test_pages_setup_is_lightweight_docs_site_configuration() -> None:
    config = yaml.safe_load((DOCS / "_config.yml").read_text(encoding="utf-8"))
    setup = (DOCS / "pages-setup.md").read_text(encoding="utf-8")

    assert config["title"] == "context-eval"
    assert config["markdown"] == "kramdown"

    for term in [
        "`docs/` directory",
        "`docs/index.md`",
        "No GitHub Pages deployment workflow is added by default",
        "Node, Vite, or external CDN",
        "frontend/` package remains",
        "not a hosted dashboard",
        "not a place to publish generated run artifacts",
        "local app remains local",
        "GitHub Pages deployment actions",
    ]:
        assert term in setup


def test_changelog_mentions_project_documentation_site() -> None:
    text = Path("CHANGELOG.md").read_text(encoding="utf-8")

    for term in [
        "project documentation site entry",
        "demo workflow",
        "architecture overview",
        "evaluation methodology",
        "artifact model",
        "FAQ",
        "GitHub Pages setup notes",
    ]:
        assert term in text
