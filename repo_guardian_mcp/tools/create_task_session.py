from __future__ import annotations

from pathlib import Path

from repo_guardian_mcp.services.session_service import SessionService
from repo_guardian_mcp.utils.git_utils import (
    create_git_worktree,
)


def create_task_session(
    repo_root: str,
    create_workspace: bool = True,
) -> dict:
    repo_root_path = Path(repo_root).resolve()

    if not repo_root_path.exists():
        return {
            "ok": False,
            "error": f"repo_root 不存在: {repo_root_path}",
        }

    runtime_root = (repo_root_path / "agent_runtime").resolve()
    sessions_root = (runtime_root / "sessions").resolve()
    sandbox_root = (runtime_root / "sandbox_worktrees").resolve()

    sessions_root.mkdir(parents=True, exist_ok=True)
    sandbox_root.mkdir(parents=True, exist_ok=True)

    session_service = SessionService(str(sessions_root))
    session_id = session_service.new_session_id()

    sandbox_path = (sandbox_root / session_id).resolve()
    branch_name = f"rg/session-{session_id}"

    # 關鍵修正：
    # 不先呼叫 get_head_commit()，直接用 HEAD 當 base_commit，
    # 避免在 Continue / MCP 環境中卡住 60 秒。
    base_commit = "HEAD"

    # 在 Continue / MCP 環境中，抓 branch 名稱有時會卡 60 秒。
    # 這個欄位只是 metadata，不是建立 session / worktree 的必要條件。
    base_branch = "unknown"

    session = session_service.build_session(
        session_id=session_id,
        repo_root=repo_root_path,
        sandbox_path=sandbox_path,
        branch_name=branch_name,
        base_branch=base_branch,
        base_commit=base_commit,
    )

    if not create_workspace:
        session.status = "pending_workspace"
        session_service.save_session(session)
        return {
            "ok": True,
            "session_id": session.session_id,
            "repo_root": session.repo_root,
            "sandbox_path": session.sandbox_path,
            "branch_name": session.branch_name,
            "base_branch": session.base_branch,
            "base_commit": session.base_commit,
            "status": session.status,
        }

    try:
        create_git_worktree(
            repo_path=repo_root_path,
            sandbox_path=sandbox_path,
            branch_name=branch_name,
            base_commit=base_commit,
        )
    except Exception as exc:
        return {
            "ok": False,
            "error": f"create_task_session 失敗: {exc}",
            "repo_root": str(repo_root_path),
            "sandbox_path": str(sandbox_path),
            "branch_name": branch_name,
            "session_id": session_id,
            "base_commit": base_commit,
            "base_branch": base_branch,
        }

    session_service.save_session(session)

    return {
        "ok": True,
        "session_id": session.session_id,
        "repo_root": session.repo_root,
        "sandbox_path": session.sandbox_path,
        "branch_name": session.branch_name,
        "base_branch": session.base_branch,
        "base_commit": session.base_commit,
        "status": session.status,
    }