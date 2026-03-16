from __future__ import annotations

from pathlib import Path

from repo_guardian_mcp.services.session_service import SessionService
from repo_guardian_mcp.utils.git_utils import (
    create_git_worktree,
    get_current_branch,
    get_head_commit,
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

    try:
        base_branch = get_current_branch(repo_root_path)
        base_commit = get_head_commit(repo_root_path)
    except Exception as exc:
        return {
            "ok": False,
            "error": f"讀取 git 基本資訊失敗: {exc}",
            "repo_root": str(repo_root_path),
        }

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
