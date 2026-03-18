from __future__ import annotations

"""
create_task_session 工具

建立新的編輯 session，負責設定 session metadata 並視需要建立 copy-based sandbox
工作區。此工具採用 copy-based sandbox（而非 git worktree），可以避免 git 操作的
複雜性並降低 Continue timeout 的機率。建立後會儲存 session 資料並回傳 session
資訊。
"""

from datetime import UTC, datetime, timedelta
from pathlib import Path

from repo_guardian_mcp.services.sandbox_service import prepare_copy_sandbox
from repo_guardian_mcp.services.session_service import SessionService
from repo_guardian_mcp.services.session_update_service import update_session_file


def create_task_session(
    repo_root: str,
    create_workspace: bool = True,
) -> dict:
    """
    建立 session。

    參數：
        repo_root (str): 專案根目錄。
        create_workspace (bool): 是否立即建立 sandbox 工作區；若為 False 只建立 session 資料。

    回傳：
        dict: 包含 ``ok``、``session_id``、``sandbox_path`` 等欄位的字典。
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

    created_at = datetime.now(UTC)
    default_expires_at = created_at + timedelta(days=3)

    # 建立 session 資料
    session = session_service.build_session(
        session_id=session_id,
        repo_root=repo_root_path,
        sandbox_path=sandbox_path,
        branch_name=branch_name,
        base_branch="copy-sandbox",
        base_commit="copy-sandbox",
    )
    session.created_at = created_at

    # 若不建立 workspace，僅更新狀態並儲存 session
    if not create_workspace:
        session.status = "pending_workspace"
        session_service.save_session(session)
        update_session_file(
            repo_root=str(repo_root_path),
            session_id=session.session_id,
            updates={
                "last_accessed_at": created_at.isoformat(),
                "expires_at": default_expires_at.isoformat(),
                "pinned": False,
                "changed": False,
                "edited_files": [],
                "summary": "Session created; workspace pending.",
                "validation": None,
            },
        )
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
        # 建立 copy-based sandbox
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
    update_session_file(
        repo_root=str(repo_root_path),
        session_id=session.session_id,
        updates={
            "last_accessed_at": created_at.isoformat(),
            "expires_at": default_expires_at.isoformat(),
            "pinned": False,
            "changed": False,
            "edited_files": [],
            "summary": "Session created and workspace ready.",
            "validation": None,
        },
    )

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