from __future__ import annotations

from pathlib import Path

from repo_guardian_mcp.services.sandbox_service import cleanup_copy_sandbox
from repo_guardian_mcp.services.session_service import SessionService


def rollback_session(
    repo_root: str,
    session_id: str,
    cleanup_workspace: bool = True,
) -> dict:
    """
    回滾 copy-based sandbox session。

    注意：
    TaskSession model 目前可寫欄位有限，
    所以這裡只更新既有欄位，不再硬塞 summary / changed。
    """
    repo_root_path = Path(repo_root).resolve()
    sessions_dir = repo_root_path / "agent_runtime" / "sessions"

    session_service = SessionService(str(sessions_dir))
    session = session_service.load_session(session_id)

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
