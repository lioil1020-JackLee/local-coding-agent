from __future__ import annotations

import json

from repo_guardian_mcp.cli import main
from repo_guardian_mcp.tools.create_task_session import create_task_session


def test_cli_skills_command(capsys):
    code = main(["skills"])
    captured = capsys.readouterr()
    assert code == 0
    assert "safe_edit" in captured.out
    assert "analyze_repo" in captured.out


def test_cli_plan_command(tmp_path, capsys):
    (tmp_path / "README.md").write_text("hello\n", encoding="utf-8")
    code = main(["plan", str(tmp_path), "--prompt", "請分析這個專案", "--task-type", "analyze"])
    captured = capsys.readouterr()
    assert code == 0
    assert '"selected_skill": "analyze_repo"' in captured.out


def test_cli_session_list_command(tmp_path, capsys):
    (tmp_path / "README.md").write_text("demo\n", encoding="utf-8")
    create_task_session(str(tmp_path), create_workspace=False)

    code = main(["session", "list", str(tmp_path)])
    captured = capsys.readouterr()

    assert code == 0
    data = json.loads(captured.out)
    assert data["ok"] is True
    assert data["count"] >= 1
    assert len(data["sessions"]) >= 1
    assert data["data"]["trace_summary"]["total"] >= 1
    assert data["data"]["standardized_trace"][0]["step"] == "session_list"


def test_cli_diff_and_rollback_commands(tmp_path, capsys):
    (tmp_path / "README.md").write_text("before\n", encoding="utf-8")
    created = create_task_session(str(tmp_path), create_workspace=True)
    session_id = created["session_id"]

    sandbox_readme = tmp_path / "agent_runtime" / "sandbox_workspaces" / session_id / "README.md"
    sandbox_readme.write_text("after\n", encoding="utf-8")

    diff_code = main(["diff", str(tmp_path), session_id])
    diff_captured = capsys.readouterr()

    assert diff_code == 0
    diff_data = json.loads(diff_captured.out)
    assert diff_data["ok"] is True
    assert diff_data["changed_file_count"] >= 1
    assert "README.md" in diff_data["changed_files"]

    rollback_code = main(["rollback", str(tmp_path), session_id])
    rollback_captured = capsys.readouterr()

    assert rollback_code == 0
    rollback_data = json.loads(rollback_captured.out)
    assert rollback_data["ok"] is True
    assert rollback_data["status"] == "rolled_back"


def test_cli_continue_config_status_and_sync(tmp_path, capsys):
    source_dir = tmp_path / "source_continue"
    target_dir = tmp_path / "target_continue"
    source_dir.mkdir()
    target_dir.mkdir()
    source_cfg = source_dir / "config.yaml"
    target_cfg = target_dir / "config.yaml"
    source_cfg.write_text("name: demo\n", encoding="utf-8")

    status_code = main(
        [
            "continue-config",
            "status",
            "--source-config",
            str(source_cfg),
            "--target-config",
            str(target_cfg),
        ]
    )
    status_captured = capsys.readouterr()
    assert status_code == 0
    status_data = json.loads(status_captured.out)
    assert status_data["ok"] is True
    assert status_data["same_content"] is False

    sync_code = main(
        [
            "continue-config",
            "sync",
            "--source-config",
            str(source_cfg),
            "--target-config",
            str(target_cfg),
        ]
    )
    sync_captured = capsys.readouterr()
    assert sync_code == 0
    sync_data = json.loads(sync_captured.out)
    assert sync_data["ok"] is True
    assert sync_data["same_content"] is True

    setup_source = tmp_path / "setup_repo" / "continue"
    setup_source.mkdir(parents=True)
    (setup_source / "config.yaml").write_text("name: setup\n", encoding="utf-8")
    setup_target = tmp_path / "setup_target" / "config.yaml"
    setup_code = main(
        [
            "continue-config",
            "setup",
            str(tmp_path / "setup_repo"),
            "--target-config",
            str(setup_target),
        ]
    )
    setup_captured = capsys.readouterr()
    assert setup_code == 0
    setup_data = json.loads(setup_captured.out)
    assert setup_data["ok"] is True
    assert setup_data["mode"] == "continue_config_setup"
    assert setup_data["ready"] is True
    assert setup_data["diagnosis"]["ok"] is True
    assert setup_target.exists()

    diagnose_code = main(
        [
            "continue-config",
            "diagnose",
            str(tmp_path / "setup_repo"),
            "--target-config",
            str(setup_target),
        ]
    )
    diagnose_captured = capsys.readouterr()
    assert diagnose_code == 0
    diagnose_data = json.loads(diagnose_captured.out)
    assert diagnose_data["ok"] is True
    assert diagnose_data["mode"] == "continue_config_diagnose"
    assert "score" in diagnose_data

    autofix_repo = tmp_path / "autofix_repo" / "continue"
    autofix_repo.mkdir(parents=True)
    (autofix_repo / "config.yaml").write_text("name: auto-source\n", encoding="utf-8")
    autofix_target = tmp_path / "autofix_target" / "config.yaml"
    autofix_target.parent.mkdir(parents=True)
    autofix_target.write_text("name: old\n", encoding="utf-8")
    autofix_code = main(
        [
            "continue-config",
            "autofix",
            str(tmp_path / "autofix_repo"),
            "--target-config",
            str(autofix_target),
        ]
    )
    autofix_captured = capsys.readouterr()
    assert autofix_code == 0
    autofix_data = json.loads(autofix_captured.out)
    assert autofix_data["ok"] is True
    assert autofix_data["mode"] == "continue_config_autofix"
    assert autofix_data["ready"] is True


def test_cli_runtime_cleanup_commands(tmp_path, capsys):
    runtime = tmp_path / "agent_runtime"
    (runtime / "sessions").mkdir(parents=True)
    (runtime / "sandbox_workspaces").mkdir(parents=True)
    (runtime / "agent_sessions").mkdir(parents=True)

    run_code = main(["runtime-cleanup", "run", str(tmp_path), "--dry-run"])
    run_captured = capsys.readouterr()
    assert run_code == 0
    run_data = json.loads(run_captured.out)
    assert run_data["ok"] is True
    assert run_data["mode"] == "runtime_cleanup_run"

    hint_code = main(["runtime-cleanup", "schedule-hint", str(tmp_path), "--time", "03:30"])
    hint_captured = capsys.readouterr()
    assert hint_code == 0
    hint_data = json.loads(hint_captured.out)
    assert hint_data["ok"] is True
    assert "schtasks /Create" in hint_data["schedule_command"]


def test_cli_runtime_cleanup_aggressive_flag(tmp_path, capsys):
    runtime = tmp_path / "agent_runtime"
    (runtime / "sessions").mkdir(parents=True)
    (runtime / "sandbox_workspaces").mkdir(parents=True)
    (runtime / "agent_sessions").mkdir(parents=True)

    code = main(["runtime-cleanup", "run", str(tmp_path), "--dry-run", "--aggressive"])
    captured = capsys.readouterr()
    assert code == 0
    data = json.loads(captured.out)
    assert data["ok"] is True
    assert data["aggressive"] is True
    assert data["applied_policy"]["session_days"] == 0


def test_cli_health_report_command(tmp_path, capsys):
    (tmp_path / "README.md").write_text("demo\n", encoding="utf-8")
    (tmp_path / "agent_runtime" / "sessions").mkdir(parents=True)
    (tmp_path / "agent_runtime" / "sandbox_workspaces").mkdir(parents=True)
    (tmp_path / "agent_runtime" / "agent_sessions").mkdir(parents=True)

    code = main(["health", "report", str(tmp_path)])
    captured = capsys.readouterr()
    assert code == 0
    data = json.loads(captured.out)
    assert data["ok"] is True
    assert data["mode"] == "health_report"
    assert "health_score" in data

    code = main(["health", "history", str(tmp_path), "--limit", "5"])
    captured = capsys.readouterr()
    assert code == 0
    hist_data = json.loads(captured.out)
    assert hist_data["ok"] is True
    assert hist_data["mode"] == "health_history"

    code = main(["health", "schedule-hint", str(tmp_path), "--time", "03:45", "--refresh-benchmark"])
    captured = capsys.readouterr()
    assert code == 0
    hint_data = json.loads(captured.out)
    assert hint_data["ok"] is True
    assert hint_data["mode"] == "health_schedule_hint"
    assert "schtasks /Create" in hint_data["schedule_command"]


def test_cli_ops_commands(tmp_path, capsys):
    (tmp_path / "README.md").write_text("demo\n", encoding="utf-8")
    (tmp_path / "agent_runtime" / "sessions").mkdir(parents=True)
    (tmp_path / "agent_runtime" / "sandbox_workspaces").mkdir(parents=True)
    (tmp_path / "agent_runtime" / "agent_sessions").mkdir(parents=True)
    (tmp_path / "continue").mkdir(parents=True)
    (tmp_path / "continue" / "config.yaml").write_text("name: demo\n", encoding="utf-8")

    code = main(
        [
            "ops",
            "preflight",
            str(tmp_path),
            "--continue-source-config",
            "continue/config.yaml",
            "--continue-target-config",
            str(tmp_path / "no_target" / "config.yaml"),
        ]
    )
    captured = capsys.readouterr()
    assert code == 0
    preflight_data = json.loads(captured.out)
    assert preflight_data["ok"] is True
    assert preflight_data["mode"] == "ops_preflight"
    assert "preflight_score" in preflight_data

    code = main(["ops", "daily", str(tmp_path)])
    captured = capsys.readouterr()
    assert code == 0
    daily_data = json.loads(captured.out)
    assert daily_data["ok"] is True
    assert daily_data["mode"] == "ops_daily"

    code = main(["ops", "snapshot", str(tmp_path), "--tag", "manual"])
    captured = capsys.readouterr()
    assert code == 0
    snap_data = json.loads(captured.out)
    assert snap_data["ok"] is True
    assert snap_data["mode"] == "ops_snapshot"
    assert "snapshot_file" in snap_data

    code = main(
        [
            "ops",
            "run",
            str(tmp_path),
            "--profile",
            "day-start",
            "--continue-source-config",
            "continue/config.yaml",
            "--continue-target-config",
            str(tmp_path / "no_target" / "config.yaml"),
        ]
    )
    captured = capsys.readouterr()
    assert code == 0
    run_data = json.loads(captured.out)
    assert run_data["ok"] is True
    assert run_data["mode"] == "ops_run"
    assert run_data["profile"] == "day-start"
