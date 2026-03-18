from __future__ import annotations

import json
from pathlib import Path

from repo_guardian_mcp.tools.cleanup_sessions import cleanup_sessions_tool
from repo_guardian_mcp.tools.list_sessions import list_sessions_tool
from repo_guardian_mcp.tools.pin_session import pin_session_tool
from repo_guardian_mcp.tools.resume_session import resume_session_tool


def _write_session(path: Path, session_id: str) -> None:
    path.write_text(
        json.dumps(
            {
                "session_id": session_id,
                "status": "completed",
                "created_at": "2026-03-18T10:00:00+00:00",
                "last_accessed_at": "2026-03-18T10:00:00+00:00",
                "expires_at": "2026-03-21T10:00:00+00:00",
                "workspace_path": str(path.parent.parent / "sandbox_workspaces" / session_id),
                "pinned": False,
            },
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )


def test_list_pin_and_resume_session(tmp_path: Path) -> None:
    sessions_dir = tmp_path / "sessions"
    sessions_dir.mkdir(parents=True)
    metadata = sessions_dir / "sess_a.json"
    _write_session(metadata, "sess_a")

    listed = list_sessions_tool(str(sessions_dir))
    assert listed["ok"] is True
    assert listed["count"] == 1
    assert listed["sessions"][0]["session_id"] == "sess_a"

    pinned = pin_session_tool(str(sessions_dir), "sess_a", pinned=True)
    assert pinned["ok"] is True
    assert pinned["pinned"] is True

    resumed = resume_session_tool(str(sessions_dir), "sess_a")
    assert resumed["ok"] is True
    assert resumed["last_accessed_at"] is not None
    assert resumed["expires_at"] is not None


def test_cleanup_sessions_tool_respects_pinned(tmp_path: Path) -> None:
    sessions_dir = tmp_path / "sessions"
    sessions_dir.mkdir(parents=True)
    metadata = sessions_dir / "sess_b.json"
    _write_session(metadata, "sess_b")

    pin_session_tool(str(sessions_dir), "sess_b", pinned=True)
    result = cleanup_sessions_tool(str(sessions_dir), days=0, max_sessions=0)

    assert result["ok"] is True
    assert result["deleted"] == 0
    assert (sessions_dir / "sess_b.json").exists()
