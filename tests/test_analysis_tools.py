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
