from __future__ import annotations

import json
from pathlib import Path

from repo_guardian_mcp.services.session_lifecycle_coordinator import SessionLifecycleCoordinator


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


def test_coordinator_touch_pin_resume_and_list(tmp_path: Path) -> None:
    sessions_dir = tmp_path / "sessions"
    sessions_dir.mkdir(parents=True)
    metadata = sessions_dir / "sess_c.json"
    _write_session(metadata, "sess_c")

    coordinator = SessionLifecycleCoordinator(sessions_dir)
    coordinator.touch_session("sess_c")
    pinned = coordinator.pin_session("sess_c", pinned=True)
    resumed = coordinator.resume_session("sess_c")
    listed = coordinator.list_sessions()

    assert pinned.pinned is True
    assert resumed.last_accessed_at is not None
    assert len(listed) == 1
    assert listed[0].session_id == "sess_c"


def test_coordinator_maybe_cleanup_can_run(tmp_path: Path) -> None:
    sessions_dir = tmp_path / "sessions"
    sessions_dir.mkdir(parents=True)
    metadata = sessions_dir / "sess_d.json"
    _write_session(metadata, "sess_d")

    coordinator = SessionLifecycleCoordinator(sessions_dir)
    result = coordinator.maybe_cleanup(probability=1.0, days=999, max_sessions=20)

    assert result is not None
    assert result.scanned == 1
