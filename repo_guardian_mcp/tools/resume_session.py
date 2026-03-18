from __future__ import annotations

from pathlib import Path

from repo_guardian_mcp.services.session_cleanup_service import FileSessionStore, SessionCleanupService


def resume_session_tool(sessions_dir: str, session_id: str) -> dict:
    """恢復既有 session 的活躍狀態，並更新 last_accessed_at / expires_at。"""

    store = FileSessionStore(Path(sessions_dir))
    service = SessionCleanupService(session_store=store)
    record = service.touch_session(session_id=session_id)
    return {
        "ok": True,
        "session_id": record.session_id,
        "status": record.status,
        "pinned": record.pinned,
        "last_accessed_at": record.last_accessed_at.isoformat() if record.last_accessed_at else None,
        "expires_at": record.expires_at.isoformat() if record.expires_at else None,
    }
