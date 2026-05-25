from pathlib import Path

from context_eval.contexts.overlay import apply_overlay
from context_eval.models import OverlayConfig


def test_apply_overlay_replaces_existing_target_file(tmp_path: Path) -> None:
    workspace = tmp_path / "workspace"
    workspace.mkdir()
    existing = workspace / "AGENTS.md"
    existing.write_text("old instructions\n", encoding="utf-8")
    source = tmp_path / "contexts" / "experiment" / "AGENTS.md"
    source.parent.mkdir(parents=True)
    source.write_text("new instructions\n", encoding="utf-8")

    apply_overlay(workspace, OverlayConfig(source=source, target="AGENTS.md"))

    assert existing.read_text(encoding="utf-8") == "new instructions\n"
