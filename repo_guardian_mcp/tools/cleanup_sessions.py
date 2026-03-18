from __future__ import annotations

from pathlib import Path

from repo_guardian_mcp.services.session_cleanup_service import FileSessionStore, SessionCleanupService


def cleanup_sessions_tool(
    sessions_dir: str,
    days: int = 3,
    max_sessions: int = 20,
    max_total_workspace_bytes: int | None = None,
) -> dict:
    """清理過期或過多的 session workspace。"""

    session_store = FileSessionStore(Path(sessions_dir))
    service = SessionCleanupService(session_store=session_store)
    result = service.cleanup_sessions(
        days=days,
        max_sessions=max_sessions,
        max_total_workspace_bytes=max_total_workspace_bytes,
    )
    return {
        "ok": True,
        "scanned": result.scanned,
        "deleted": result.deleted,
        "reclaimed_bytes": result.reclaimed_bytes,
        "deleted_session_ids": result.deleted_session_ids,
        "skipped_pinned": result.skipped_pinned,
        "skipped_active": result.skipped_active,
        "decisions": [
            {
                "session_id": decision.session_id,
                "reason": decision.reason,
                "reclaimed_bytes": decision.reclaimed_bytes,
            }
            for decision in result.decisions
        ],
    }
