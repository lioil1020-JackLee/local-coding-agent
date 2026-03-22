from __future__ import annotations

from repo_guardian_mcp.services.health_report_service import HealthReportService


def test_health_report_service_generates_report(tmp_path):
    (tmp_path / "README.md").write_text("demo\n", encoding="utf-8")
    runtime = tmp_path / "agent_runtime"
    (runtime / "sessions").mkdir(parents=True)
    (runtime / "sandbox_workspaces").mkdir(parents=True)
    (runtime / "agent_sessions").mkdir(parents=True)

    svc = HealthReportService()
    out = svc.report(repo_root=str(tmp_path), refresh_benchmark=False, threshold=0.85)
    assert out["ok"] is True
    assert "health_score" in out
    assert out["health_level"] in {"good", "warning", "critical"}
    assert isinstance(out["issues"], list)
    assert isinstance(out["next_actions"], list)
    assert "report_file" in out
    assert "latest_file" in out

    hist = svc.history(repo_root=str(tmp_path), limit=10)
    assert hist["ok"] is True
    assert hist["count"] >= 1
    assert hist["items"][0]["health_level"] in {"good", "warning", "critical"}


def test_health_report_service_schedule_hint():
    svc = HealthReportService()
    out = svc.build_windows_schedule_hint(
        repo_root=r"E:\py\local-coding-agent",
        at_time="03:45",
        task_name="RepoGuardianHealthReport",
        refresh_benchmark=True,
    )
    assert out["ok"] is True
    assert "schtasks /Create" in out["schedule_command"]
