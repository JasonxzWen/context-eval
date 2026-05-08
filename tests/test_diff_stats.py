import subprocess
from pathlib import Path

from context_eval.evaluators.diff import collect_git_diff, create_diff_baseline, parse_numstat


def test_parse_git_diff_numstat() -> None:
    output = "\n".join(
        [
            "10\t2\tcontext_eval/runner.py",
            "5\t0\tREADME.md",
            "-\t-\tassets/logo.png",
            "",
        ]
    )

    stats = parse_numstat(output)

    assert stats.changed_files == 3
    assert stats.insertions == 15
    assert stats.deletions == 2
    assert stats.touched_paths == [
        "context_eval/runner.py",
        "README.md",
        "assets/logo.png",
    ]


def test_collect_git_diff_uses_overlay_baseline(tmp_path: Path) -> None:
    repo = tmp_path / "repo"
    repo.mkdir()
    subprocess.run(["git", "init"], cwd=repo, check=True, stdout=subprocess.PIPE)
    (repo / "README.md").write_text("base\n", encoding="utf-8")
    subprocess.run(["git", "add", "README.md"], cwd=repo, check=True)
    subprocess.run(
        [
            "git",
            "-c",
            "user.email=test@example.com",
            "-c",
            "user.name=Test",
            "commit",
            "-m",
            "init",
        ],
        cwd=repo,
        check=True,
        stdout=subprocess.PIPE,
    )

    (repo / "AGENTS.md").write_text("overlay instructions\n", encoding="utf-8")
    (repo / "README.md").write_text("base\noverlay line\n", encoding="utf-8")
    index_file = tmp_path / "baseline.index"
    baseline_tree = create_diff_baseline(repo, index_file)

    (repo / "README.md").write_text("base\noverlay line\nagent line\n", encoding="utf-8")
    (repo / "new_file.py").write_text("print('new')\n", encoding="utf-8")
    stats = collect_git_diff(repo, tmp_path / "patch.diff", baseline_tree, index_file)

    assert stats.changed_files == 2
    assert stats.insertions == 2
    assert stats.touched_paths == ["README.md", "new_file.py"]
