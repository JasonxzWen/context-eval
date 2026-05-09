from pathlib import Path


def test_ralph_loop_uses_current_codex_approval_flag() -> None:
    script = Path("scripts/ralph/ralph.ps1").read_text(encoding="utf-8")

    assert '"-a", $Approval' in script
    assert '"--ask-for-approval", $Approval' not in script


def test_ralph_loop_checks_only_last_codex_message_for_completion() -> None:
    script = Path("scripts/ralph/ralph.ps1").read_text(encoding="utf-8")

    assert "$lastMessageFile" in script
    assert "-o", "$lastMessageFile" in script
    assert "$lastMessageText -match" in script
    assert "$text -match" not in script


def test_ralph_loop_allows_codex_stderr_warnings() -> None:
    script = Path("scripts/ralph/ralph.ps1").read_text(encoding="utf-8")

    assert '$previousErrorActionPreference = $ErrorActionPreference' in script
    assert '$ErrorActionPreference = "Continue"' in script
    assert "$ErrorActionPreference = $previousErrorActionPreference" in script
