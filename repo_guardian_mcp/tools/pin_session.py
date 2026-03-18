from __future__ import annotations

from pathlib import Path

from repo_guardian_mcp.services.session_cleanup_service import FileSessionStore, SessionCleanupService


def pin_session_tool(sessions_dir: str, session_id: str, pinned: bool = True) -> dict:
    """將 session 標記為 pinned / unpinned。"""

    session_store = FileSessionStore(Path(sessions_dir))
    service = SessionCleanupService(session_store=session_store)
    record = service.pin_session(session_id=session_id, pinned=pinned)
    return {
        "ok": True,
        "session_id": record.session_id,
        "pinned": record.pinned,
        "status": record.status,
    }
