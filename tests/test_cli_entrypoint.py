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
