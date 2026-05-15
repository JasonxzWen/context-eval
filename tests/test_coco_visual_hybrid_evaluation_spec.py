from pathlib import Path


def test_coco_visual_hybrid_spec_documents_required_contract() -> None:
    text = Path("docs/coco-visual-hybrid-evaluation.md").read_text(encoding="utf-8")

    for heading in [
        "## User Workflow",
        "## Coco-first Agent Profile Configuration",
        "## Task Authoring Model",
        "## Expected Outcome Model",
        "## Hard Evaluation Model",
        "## Optional Soft Evaluation Model",
        "## Local App UI Workflow",
        "## Local App API Workflow",
        "## Artifact Schema Additions",
        "## Non-goals",
        "## Test Plan",
    ]:
        assert heading in text

    for term in [
        'kind: "coco"',
        'coco -y --query-timeout 10m --bash-tool-timeout 5m -p "{prompt}"',
        "--allowed-tool",
        "expected_outcome",
        "hard_evaluation",
        "soft_evaluation",
        "payload-only",
        "artifacts/<case_id>/hard_evaluation.json",
        "artifacts/<case_id>/soft_evaluation_payload.json",
        "does not install Coco",
        "does not manage Coco credentials",
        "does not call hosted model APIs directly",
        "does not infer token counts",
    ]:
        assert term in text


def test_development_plan_marks_coco_visual_hybrid_as_next_capability() -> None:
    text = Path("docs/development-plan.md").read_text(encoding="utf-8")

    for term in [
        "The next active capability is `coco-visual-hybrid-evaluation`",
        "Current active capability: `coco-visual-hybrid-evaluation`",
        "docs/coco-visual-hybrid-evaluation.md",
        'kind: "coco"',
        "deterministic hard checks",
        "optional soft evaluation payload",
    ]:
        assert term in text


def test_openspec_change_defines_coco_visual_hybrid_capability() -> None:
    change = Path("openspec/changes/coco-visual-hybrid-evaluation")

    for relative in [
        "proposal.md",
        "design.md",
        "tasks.md",
        "specs/coco-visual-hybrid-evaluation/spec.md",
        "specs/agent-profiles/spec.md",
        "specs/local-app-workflow/spec.md",
    ]:
        assert (change / relative).exists()

    spec = (change / "specs/coco-visual-hybrid-evaluation/spec.md").read_text(
        encoding="utf-8"
    )
    for term in [
        "### Requirement: Coco-first local profile support",
        "#### Scenario: Coco profile validates",
        "### Requirement: Structured task authoring model",
        "### Requirement: Deterministic hard evaluation artifacts",
        "### Requirement: Optional soft evaluation payload",
        "### Requirement: Local app visual workflow",
        "### Requirement: Reports and exports expose stable evaluation fields",
    ]:
        assert term in spec
