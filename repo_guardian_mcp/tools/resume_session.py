from __future__ import annotations

from pathlib import Path

from repo_guardian_mcp.services.session_lifecycle_coordinator import SessionLifecycleCoordinator


_NON_RESUMABLE_STATUSES = {"rolled_back", "cleaned"}


def _find_session_record(sessions_dir: Path, session_id: str):
    coordinator = SessionLifecycleCoordinator(sessions_dir)
    for record in coordinator.list_sessions():
        if record.session_id == session_id:
            return record
    return None


def resume_session_tool(sessions_dir: str, session_id: str) -> dict:
    sessions_path = Path(sessions_dir)
    record = _find_session_record(sessions_path, session_id)

    if record is None:
        return {
            "ok": False,
            "session_id": session_id,
            "error": f"找不到 session metadata: {session_id}",
        }

    if record.status in _NON_RESUMABLE_STATUSES:
        return {
            "ok": False,
            "session_id": session_id,
            "status": record.status,
            "error": f"session 狀態為 {record.status}，不可 resume。",
        }

    touched = SessionLifecycleCoordinator(sessions_path).resume_session(session_id=session_id)
    return {
        "ok": True,
        "session_id": touched.session_id,
        "status": touched.status,
        "pinned": touched.pinned,
        "last_accessed_at": touched.last_accessed_at.isoformat() if touched.last_accessed_at else None,
        "expires_at": touched.expires_at.isoformat() if touched.expires_at else None,
        "workspace_path": str(touched.workspace_path) if touched.workspace_path else None,
    }
