from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict

from repo_guardian_mcp.services.session_lifecycle_coordinator import SessionLifecycleCoordinator


def get_session_status(repo_root: str, session_id: str) -> Dict[str, Any]:
    if not repo_root or not repo_root.strip():
        return {"ok": False, "error": "repo_root 不能為空"}

    if not session_id or not session_id.strip():
        return {"ok": False, "error": "session_id 不能為空"}

    session_file = Path(repo_root) / "agent_runtime" / "sessions" / f"{session_id}.json"
    if not session_file.exists():
        return {"ok": False, "error": f"找不到 session 檔案: {session_file}", "session_id": session_id}

    SessionLifecycleCoordinator(session_file.parent).touch_session(session_id=session_id)
    data = json.loads(session_file.read_text(encoding="utf-8"))

    if not isinstance(data, dict):
        return {"ok": False, "error": "session 檔案內容不是 dict", "session_id": session_id}

    return {
        "ok": True,
        "session_id": session_id,
        "session_file": str(session_file),
        "status": data.get("status"),
        "changed": data.get("changed"),
        "edited_files": data.get("edited_files", []),
        "summary": data.get("summary"),
        "validation": data.get("validation"),
        "pinned": data.get("pinned", False),
        "last_accessed_at": data.get("last_accessed_at"),
        "expires_at": data.get("expires_at"),
        "session": data,
    }
