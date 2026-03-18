from __future__ import annotations

import json
import subprocess
from datetime import datetime, timedelta, timezone
from pathlib import Path

from repo_guardian_mcp.services.session_cleanup_service import FileSessionStore, SessionCleanupService

UTC = timezone.utc


def _git(repo: Path, *args: str) -> str:
    result = subprocess.run(
        ["git", *args],
        cwd=repo,
        capture_output=True,
        text=True,
        check=True,
    )
    return result.stdout.strip()


def test_cleanup_sessions_removes_session_branch_and_sandbox_paths(tmp_path: Path) -> None:
    repo = tmp_path / "repo"
    repo.mkdir()
    _git(repo, "init", "-b", "main")
    _git(repo, "config", "user.email", "test@example.com")
    _git(repo, "config", "user.name", "Test User")
    (repo / "README.md").write_text("hello\n", encoding="utf-8")
    _git(repo, "add", "README.md")
    _git(repo, "commit", "-m", "init")

    runtime = repo / "agent_runtime"
    sessions_dir = runtime / "sessions"
    workspaces_dir = runtime / "sandbox_workspaces"
    worktrees_dir = runtime / "sandbox_worktrees"
    sessions_dir.mkdir(parents=True)
    workspaces_dir.mkdir(parents=True)
    worktrees_dir.mkdir(parents=True)

    session_id = "sessabc123456"
    branch_name = f"rg/session-{session_id}"

    workspace_path = workspaces_dir / session_id
    workspace_path.mkdir()
    (workspace_path / "payload.txt").write_text("x" * 20, encoding="utf-8")

    sandbox_worktree_path = worktrees_dir / session_id
    sandbox_worktree_path.mkdir()
    (sandbox_worktree_path / "dummy.txt").write_text("dummy\n", encoding="utf-8")

    # 只建立 branch，不在 Windows 測試中真的建立 git worktree，避免環境差異造成失敗
    _git(repo, "branch", branch_name)

    data = {
        "session_id": session_id,
        "status": "completed",
        "pinned": False,
        "created_at": "2026-03-15T00:00:00Z",
        "last_accessed_at": (datetime.now(UTC) - timedelta(days=10)).isoformat().replace("+00:00", "Z"),
        "expires_at": (datetime.now(UTC) - timedelta(days=1)).isoformat().replace("+00:00", "Z"),
        "workspace_path": str(workspace_path),
        "sandbox_path": str(workspace_path),
        "worktree_path": str(sandbox_worktree_path),
        "repo_root": str(repo),
        "branch_name": branch_name,
    }
    (sessions_dir / f"{session_id}.json").write_text(
        json.dumps(data, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    service = SessionCleanupService(FileSessionStore(sessions_dir))
    result = service.cleanup_sessions(days=3, max_sessions=20)

    assert result.deleted == 1
    assert (sessions_dir / f"{session_id}.json").exists() is False
    assert workspace_path.exists() is False
    assert sandbox_worktree_path.exists() is False
    assert branch_name not in _git(repo, "branch", "--list", branch_name)

    # prune 至少不應失敗；沒有真實 worktree registry 時，list 只需仍可正常執行
    _git(repo, "worktree", "prune", "-v")
    _git(repo, "worktree", "list")
