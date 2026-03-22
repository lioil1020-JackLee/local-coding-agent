from __future__ import annotations

from repo_guardian_mcp.services.ops_service import OpsService


def test_ops_service_preflight_daily_snapshot(tmp_path):
    (tmp_path / "README.md").write_text("demo\n", encoding="utf-8")
    runtime = tmp_path / "agent_runtime"
    (runtime / "sessions").mkdir(parents=True)
    (runtime / "sandbox_workspaces").mkdir(parents=True)
    (runtime / "agent_sessions").mkdir(parents=True)
    (tmp_path / "continue").mkdir()
    (tmp_path / "continue" / "config.yaml").write_text("name: demo\n", encoding="utf-8")

    svc = OpsService()
    preflight = svc.preflight(
        repo_root=str(tmp_path),
        continue_source_config="continue/config.yaml",
        continue_target_config=str(tmp_path / "not_exists" / "config.yaml"),
    )
    assert preflight["ok"] is True
    assert "preflight_score" in preflight
    assert isinstance(preflight["checks"], list)

    daily = svc.daily(repo_root=str(tmp_path), refresh_benchmark=False)
    assert daily["ok"] is True
    assert "health" in daily

    snap = svc.snapshot(repo_root=str(tmp_path), tag="test")
    assert snap["ok"] is True
    assert "snapshot_file" in snap


def test_ops_service_run_profiles(tmp_path):
    (tmp_path / "README.md").write_text("demo\n", encoding="utf-8")
    runtime = tmp_path / "agent_runtime"
    (runtime / "sessions").mkdir(parents=True)
    (runtime / "sandbox_workspaces").mkdir(parents=True)
    (runtime / "agent_sessions").mkdir(parents=True)
    (tmp_path / "continue").mkdir()
    (tmp_path / "continue" / "config.yaml").write_text("name: demo\n", encoding="utf-8")

    svc = OpsService()
    out1 = svc.run(
        repo_root=str(tmp_path),
        profile="day-start",
        continue_source_config="continue/config.yaml",
        continue_target_config=str(tmp_path / "missing" / "config.yaml"),
    )
    assert out1["ok"] is True
    assert out1["profile"] == "day-start"

    out2 = svc.run(
        repo_root=str(tmp_path),
        profile="day-end",
        continue_source_config="continue/config.yaml",
        continue_target_config=str(tmp_path / "missing" / "config.yaml"),
        snapshot_tag="day-end-test",
    )
    assert out2["ok"] is True
    assert out2["profile"] == "day-end"
    assert "snapshot" in out2

    out3 = svc.run(
        repo_root=str(tmp_path),
        profile="release-check",
        continue_source_config="continue/config.yaml",
        continue_target_config=str(tmp_path / "missing" / "config.yaml"),
    )
    assert out3["ok"] is True
    assert out3["profile"] == "release-check"
    assert "ready" in out3
