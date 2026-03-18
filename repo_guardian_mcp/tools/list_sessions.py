from __future__ import annotations

from pathlib import Path

from repo_guardian_mcp.services.session_lifecycle_coordinator import SessionLifecycleCoordinator


def list_sessions_tool(sessions_dir: str, include_cleaned: bool = False) -> dict:
    records = []
    for record in SessionLifecycleCoordinator(Path(sessions_dir)).list_sessions():
        if not include_cleaned and record.status == "cleaned":
            continue
        records.append({
            "session_id": record.session_id,
            "status": record.status,
            "pinned": record.pinned,
            "created_at": record.created_at.isoformat() if record.created_at else None,
            "last_accessed_at": record.last_accessed_at.isoformat() if record.last_accessed_at else None,
            "expires_at": record.expires_at.isoformat() if record.expires_at else None,
            "workspace_path": str(record.workspace_path) if record.workspace_path else None,
        })

    records.sort(key=lambda item: item.get("last_accessed_at") or "", reverse=True)
    return {"ok": True, "count": len(records), "sessions": records}
