from __future__ import annotations

from pathlib import Path

from repo_guardian_mcp.services.session_lifecycle_coordinator import SessionLifecycleCoordinator


def resume_session_tool(sessions_dir: str, session_id: str) -> dict:
    record = SessionLifecycleCoordinator(Path(sessions_dir)).resume_session(session_id=session_id)
    return {
        "ok": True,
        "session_id": record.session_id,
        "status": record.status,
        "pinned": record.pinned,
        "last_accessed_at": record.last_accessed_at.isoformat() if record.last_accessed_at else None,
        "expires_at": record.expires_at.isoformat() if record.expires_at else None,
    }
