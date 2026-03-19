from __future__ import annotations

"""
rollback_session 工具

此工具用於回滾 copy-based sandbox session。它會視需要刪除 sandbox 資料夾，並
更新 session 狀態為 ``rolled_back``。目前 TaskSession model 可寫欄位有限，所以
僅更新既有欄位，不會新增 summary 或 changed。
"""

from pathlib import Path

from repo_guardian_mcp.services.sandbox_service import cleanup_copy_sandbox
from repo_guardian_mcp.services.session_service import SessionService
from repo_guardian_mcp.utils.paths import resolve_repo_root


def rollback_session(
    repo_root: str,
    session_id: str,
    cleanup_workspace: bool = True,
) -> dict:
    """
    回滾指定的 copy-based sandbox session。

    參數：
        repo_root (str): 專案根目錄。
        session_id (str): 要回滾的 session ID。
        cleanup_workspace (bool): 是否刪除 sandbox 工作區，預設 True。

    回傳：
        dict: 包含 ``ok``、``session_id``、``status``、``sandbox_path`` 的字典。
    """
    repo_root_path = resolve_repo_root(repo_root)
    sessions_dir = repo_root_path / "agent_runtime" / "sessions"

    session_service = SessionService(str(sessions_dir))
    session = session_service.load_session(session_id)

    # 如需要刪除 sandbox 目錄
    if cleanup_workspace and session.sandbox_path:
        cleanup_copy_sandbox(session.sandbox_path)

    session.status = "rolled_back"
    session_service.save_session(session)

    return {
        "ok": True,
        "session_id": session_id,
        "status": session.status,
        "sandbox_path": session.sandbox_path,
        "cleaned": cleanup_workspace,
        "summary": f"Session {session_id} rolled back.",
    }