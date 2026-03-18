from __future__ import annotations

from datetime import datetime, timedelta, timezone
from pathlib import Path
import json

from repo_guardian_mcp.services.session_cleanup_service import FileSessionStore, SessionCleanupService


UTC = timezone.utc


def _write_session(
    sessions_dir: Path,
    workspaces_dir: Path,
    session_id: str,
    *,
    status: str = "completed",
    pinned: bool = False,
    last_accessed_at: datetime | None = None,
    expires_at: datetime | None = None,
    payload_size: int = 64,
) -> None:
    workspace_path = workspaces_dir / session_id
    workspace_path.mkdir(parents=True, exist_ok=True)
    (workspace_path / "payload.txt").write_text("x" * payload_size, encoding="utf-8")

    data = {
        "session_id": session_id,
        "status": status,
        "pinned": pinned,
        "created_at": "2026-03-15T00:00:00Z",
        "last_accessed_at": (last_accessed_at or datetime(2026, 3, 15, tzinfo=UTC)).isoformat().replace("+00:00", "Z"),
        "expires_at": expires_at.isoformat().replace("+00:00", "Z") if expires_at else None,
        "workspace_path": str(workspace_path),
    }
    (sessions_dir / f"{session_id}.json").write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


def test_cleanup_sessions_respects_ttl_and_pinned(tmp_path: Path) -> None:
    sessions_dir = tmp_path / "sessions"
    workspaces_dir = tmp_path / "sandbox_workspaces"
    sessions_dir.mkdir()
    workspaces_dir.mkdir()

    now = datetime(2026, 3, 19, tzinfo=UTC)
    _write_session(
        sessions_dir,
        workspaces_dir,
        "expired",
        last_accessed_at=now - timedelta(days=10),
        expires_at=now - timedelta(days=1),
    )
    _write_session(
        sessions_dir,
        workspaces_dir,
        "pinned",
        pinned=True,
        last_accessed_at=now - timedelta(days=10),
        expires_at=now - timedelta(days=1),
    )
    _write_session(
        sessions_dir,
        workspaces_dir,
        "active",
        status="active",
        last_accessed_at=now - timedelta(days=10),
        expires_at=now - timedelta(days=1),
    )

    service = SessionCleanupService(FileSessionStore(sessions_dir))
    result = service.cleanup_sessions(days=3, max_sessions=20, now=now)

    assert result.deleted == 1
    assert result.deleted_session_ids == ["expired"]
    assert (sessions_dir / "expired.json").exists() is False
    assert (sessions_dir / "pinned.json").exists() is True
    assert (sessions_dir / "active.json").exists() is True


def test_cleanup_sessions_applies_lru_when_max_sessions_exceeded(tmp_path: Path) -> None:
    sessions_dir = tmp_path / "sessions"
    workspaces_dir = tmp_path / "sandbox_workspaces"
    sessions_dir.mkdir()
    workspaces_dir.mkdir()

    now = datetime(2026, 3, 19, tzinfo=UTC)
    _write_session(sessions_dir, workspaces_dir, "oldest", last_accessed_at=now - timedelta(days=2))
    _write_session(sessions_dir, workspaces_dir, "middle", last_accessed_at=now - timedelta(days=1))
    _write_session(sessions_dir, workspaces_dir, "newest", last_accessed_at=now - timedelta(hours=1))

    service = SessionCleanupService(FileSessionStore(sessions_dir))
    result = service.cleanup_sessions(days=30, max_sessions=2, now=now)

    assert result.deleted == 1
    assert result.deleted_session_ids == ["oldest"]
    assert (sessions_dir / "oldest.json").exists() is False
    assert (sessions_dir / "middle.json").exists() is True
    assert (sessions_dir / "newest.json").exists() is True


def test_pin_and_touch_session_update_metadata(tmp_path: Path) -> None:
    sessions_dir = tmp_path / "sessions"
    workspaces_dir = tmp_path / "sandbox_workspaces"
    sessions_dir.mkdir()
    workspaces_dir.mkdir()

    _write_session(sessions_dir, workspaces_dir, "session-1")
    service = SessionCleanupService(FileSessionStore(sessions_dir))

    pinned_record = service.pin_session("session-1", pinned=True)
    assert pinned_record.pinned is True

    touched_at = datetime(2026, 3, 19, 12, 0, tzinfo=UTC)
    touched_record = service.touch_session("session-1", now=touched_at, ttl_days=3)
    assert touched_record.last_accessed_at == touched_at
    assert touched_record.expires_at == touched_at + timedelta(days=3)
