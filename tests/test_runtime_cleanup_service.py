from __future__ import annotations

import json
from datetime import datetime, timedelta, timezone
from pathlib import Path

from repo_guardian_mcp.services.runtime_cleanup_service import RuntimeCleanupService


def _write_json(path: Path, data: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")


def test_runtime_cleanup_removes_old_session_workspace_and_orphans(tmp_path):
    repo_root = tmp_path
    runtime_root = repo_root / "agent_runtime"
    sessions_dir = runtime_root / "sessions"
    workspaces_dir = runtime_root / "sandbox_workspaces"
    agent_sessions_dir = runtime_root / "agent_sessions"
    sessions_dir.mkdir(parents=True)
    workspaces_dir.mkdir(parents=True)
    agent_sessions_dir.mkdir(parents=True)

    old_sid = "old001"
    active_sid = "active001"
    old_workspace = workspaces_dir / old_sid
    active_workspace = workspaces_dir / active_sid
    orphan_workspace = workspaces_dir / "orphan001"
    for p in (old_workspace, active_workspace, orphan_workspace):
        p.mkdir(parents=True)
        (p / "x.txt").write_text("hello", encoding="utf-8")

    now = datetime.now(timezone.utc)
    old_ts = (now - timedelta(days=10)).isoformat()
    _write_json(
        sessions_dir / f"{old_sid}.json",
        {
            "session_id": old_sid,
            "status": "completed",
            "workspace_path": str(old_workspace),
            "created_at": old_ts,
            "last_accessed_at": old_ts,
            "expires_at": old_ts,
        },
    )
    _write_json(
        sessions_dir / f"{active_sid}.json",
        {
            "session_id": active_sid,
            "status": "workspace_ready",
            "workspace_path": str(active_workspace),
            "created_at": now.isoformat(),
        },
    )
    old_agent_session = agent_sessions_dir / "agent-old.json"
    old_agent_session.write_text("{}", encoding="utf-8")
    old_epoch = (now - timedelta(days=20)).timestamp()
    old_agent_session.touch()
    import os

    os.utime(old_agent_session, (old_epoch, old_epoch))

    orphan_epoch = (now - timedelta(days=10)).timestamp()
    os.utime(orphan_workspace, (orphan_epoch, orphan_epoch))

    svc = RuntimeCleanupService()
    out = svc.run(
        repo_root=str(repo_root),
        session_days=3,
        max_sessions=20,
        agent_session_days=14,
        keep_last_agent_sessions=0,
        orphan_workspace_days=3,
        dry_run=False,
    )

    assert out["ok"] is True
    assert out["sessions_deleted"] >= 1
    assert out["orphan_workspaces_deleted"] >= 1
    assert out["agent_sessions_deleted"] >= 1
    assert not old_workspace.exists()
    assert active_workspace.exists()
    assert not orphan_workspace.exists()
    assert not old_agent_session.exists()


def test_runtime_cleanup_schedule_hint():
    svc = RuntimeCleanupService()
    out = svc.build_windows_schedule_hint(repo_root=r"E:\py\local-coding-agent", at_time="03:30")
    assert out["ok"] is True
    assert "schtasks /Create" in out["schedule_command"]


def test_runtime_cleanup_aggressive_overrides_policy(tmp_path):
    runtime = tmp_path / "agent_runtime"
    (runtime / "sessions").mkdir(parents=True)
    (runtime / "sandbox_workspaces").mkdir(parents=True)
    (runtime / "agent_sessions").mkdir(parents=True)
    svc = RuntimeCleanupService()
    out = svc.run(
        repo_root=str(tmp_path),
        session_days=30,
        max_sessions=999,
        agent_session_days=30,
        keep_last_agent_sessions=999,
        orphan_workspace_days=30,
        dry_run=True,
        aggressive=True,
    )
    assert out["ok"] is True
    assert out["aggressive"] is True
    assert out["applied_policy"]["session_days"] == 0
    assert out["applied_policy"]["max_sessions"] == 0
    assert out["applied_policy"]["agent_session_days"] == 0
    assert out["applied_policy"]["keep_last_agent_sessions"] == 0
    assert out["applied_policy"]["orphan_workspace_days"] == 0
