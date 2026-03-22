from __future__ import annotations

from pathlib import Path

from repo_guardian_mcp.tools.analyze_repo import analyze_repo_tool
from repo_guardian_mcp.tools.find_entrypoints import find_entrypoints


def test_analyze_repo_excludes_agent_runtime(tmp_path: Path) -> None:
    (tmp_path / "repo_guardian_mcp").mkdir()
    (tmp_path / "repo_guardian_mcp" / "server.py").write_text("print('server')\n", encoding="utf-8")
    (tmp_path / "README.md").write_text("demo\n", encoding="utf-8")

    sandbox_server = tmp_path / "agent_runtime" / "sandbox_worktrees" / "abc123" / "repo_guardian_mcp"
    sandbox_server.mkdir(parents=True)
    (sandbox_server / "server.py").write_text("print('sandbox')\n", encoding="utf-8")

    result = analyze_repo_tool(str(tmp_path))

    assert result["ok"] is True
    assert "repo_guardian_mcp/server.py" in result["entrypoints"]
    assert all("agent_runtime/sandbox_worktrees" not in item for item in result["entrypoints"])


def test_find_entrypoints_excludes_sandbox_worktrees(tmp_path: Path) -> None:
    (tmp_path / "src").mkdir()
    (tmp_path / "src" / "main.py").write_text("print('real')\n", encoding="utf-8")

    sandbox_main = tmp_path / "agent_runtime" / "sandbox_worktrees" / "sess1" / "src"
    sandbox_main.mkdir(parents=True)
    (sandbox_main / "main.py").write_text("print('sandbox')\n", encoding="utf-8")

    result = find_entrypoints(str(tmp_path))

    assert result["ok"] is True
    assert "src/main.py" in result["entrypoints"]
    assert all("agent_runtime/sandbox_worktrees" not in item for item in result["entrypoints"])


def test_analyze_repo_includes_python_evidence_and_completion(tmp_path: Path) -> None:
    (tmp_path / "app").mkdir(parents=True)
    (tmp_path / "README.md").write_text("demo\n", encoding="utf-8")
    (tmp_path / "pyproject.toml").write_text("[project]\nname='demo'\n", encoding="utf-8")
    (tmp_path / "app" / "main.py").write_text(
        "def run():\n    return 'ok'\n\nif __name__ == '__main__':\n    run()\n",
        encoding="utf-8",
    )

    result = analyze_repo_tool(str(tmp_path))

    assert result["ok"] is True
    assert int(result["python_files_total"]) >= 1
    assert int(result["python_files_sampled"]) >= 1
    assert any(item.get("path") == "app/main.py" for item in result["python_evidence"])
    completion = result["completion_estimate"]
    assert completion["is_heuristic"] is True
    assert isinstance(completion["score"], int)


def test_analyze_repo_read_all_python_reads_every_file(tmp_path: Path) -> None:
    (tmp_path / "pkg").mkdir(parents=True)
    (tmp_path / "pkg" / "a.py").write_text("def a():\n    return 1\n", encoding="utf-8")
    (tmp_path / "pkg" / "b.py").write_text("class B:\n    pass\n", encoding="utf-8")

    result = analyze_repo_tool(str(tmp_path), read_all_python=True, sample_limit=1)

    assert result["ok"] is True
    assert result["python_files_total"] == 2
    assert result["python_files_scanned_count"] == 2
    assert result["all_python_read"] is True
    assert result["python_scan_mode"] == "all"
    paths = [item["path"] for item in result["python_evidence"]]
    assert "pkg/a.py" in paths
    assert "pkg/b.py" in paths
