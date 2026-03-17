from __future__ import annotations

from pathlib import Path

from repo_guardian_mcp.services.sandbox_service import prepare_copy_sandbox
from repo_guardian_mcp.services.session_service import SessionService


def create_task_session(
    repo_root: str,
    create_workspace: bool = True,
) -> dict:
    """
    建立 session。

    方案 B：
    不再使用 git worktree，
    改成 copy-based sandbox。

    這樣的好處：
    - 建立 session 時不會卡在 git worktree
    - Continue MCP 比較不容易 timeout
    - 對 README / 單檔修改這種常見任務更穩
    """
    repo_root_path = Path(repo_root).resolve()

    if not repo_root_path.exists():
        return {
            "ok": False,
            "error": f"repo_root 不存在: {repo_root_path}",
        }

    runtime_root = (repo_root_path / "agent_runtime").resolve()
    sessions_root = (runtime_root / "sessions").resolve()
    sandbox_root = (runtime_root / "sandbox_workspaces").resolve()

    sessions_root.mkdir(parents=True, exist_ok=True)
    sandbox_root.mkdir(parents=True, exist_ok=True)

    session_service = SessionService(str(sessions_root))
    session_id = session_service.new_session_id()

    sandbox_path = (sandbox_root / session_id).resolve()
    branch_name = f"rg/session-{session_id}"

    session = session_service.build_session(
        session_id=session_id,
        repo_root=repo_root_path,
        sandbox_path=sandbox_path,
        branch_name=branch_name,
        base_branch="copy-sandbox",
        base_commit="copy-sandbox",
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
        prepare_copy_sandbox(
            repo_root=repo_root_path,
            sandbox_path=sandbox_path,
        )
        session.status = "workspace_ready"
    except Exception as exc:
        return {
            "ok": False,
            "error": f"create_task_session 失敗: {exc}",
            "repo_root": str(repo_root_path),
            "sandbox_path": str(sandbox_path),
            "branch_name": branch_name,
            "session_id": session_id,
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
