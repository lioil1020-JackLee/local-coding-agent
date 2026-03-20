import json

from repo_guardian_mcp.cli import main
from repo_guardian_mcp.services.cli_chat_service import CLIChatService
from repo_guardian_mcp.tools.create_task_session import create_task_session


def test_chat_service_session_list_command(tmp_path):
    (tmp_path / "README.md").write_text("demo\n", encoding="utf-8")
    create_task_session(str(tmp_path), create_workspace=False)

    service = CLIChatService()
    result = service.handle_input(repo_root=str(tmp_path), raw_text="/session list")

    assert result.ok is True
    assert result.mode == "session_list"
    assert result.payload["count"] >= 1
    assert "resumable" in result.payload["sessions"][0]


def test_chat_service_explicit_diff_and_rollback_command(tmp_path):
    (tmp_path / "README.md").write_text("before\n", encoding="utf-8")
    created = create_task_session(str(tmp_path), create_workspace=True)
    session_id = created["session_id"]
    sandbox_readme = tmp_path / "agent_runtime" / "sandbox_workspaces" / session_id / "README.md"
    sandbox_readme.write_text("after\n", encoding="utf-8")

    service = CLIChatService()
    diff_result = service.handle_input(repo_root=str(tmp_path), raw_text=f"/diff {session_id}")
    rollback_result = service.handle_input(repo_root=str(tmp_path), raw_text=f"/rollback {session_id}")

    assert diff_result.ok is True
    assert diff_result.mode == "diff"
    assert "README.md" in diff_result.payload["changed_files"]
    assert rollback_result.ok is True
    assert rollback_result.mode == "rollback"
    assert rollback_result.payload["status"] == "rolled_back"


def test_cli_chat_once_supports_session_list(tmp_path, capsys):
    (tmp_path / "README.md").write_text("demo\n", encoding="utf-8")
    create_task_session(str(tmp_path), create_workspace=False)

    code = main(["chat", str(tmp_path), "--message", "/session list", "--once"])
    captured = capsys.readouterr()

    assert code == 0
    data = json.loads(captured.out)
    assert data["mode"] == "session_list"
    assert data["count"] >= 1


def test_session_resume_rejects_rolled_back_session(tmp_path):
    (tmp_path / "README.md").write_text("before\n", encoding="utf-8")
    created = create_task_session(str(tmp_path), create_workspace=True)
    session_id = created["session_id"]

    service = CLIChatService()
    rollback_result = service.handle_input(repo_root=str(tmp_path), raw_text=f"/rollback {session_id}")
    assert rollback_result.ok is True

    resumed = service.handle_input(repo_root=str(tmp_path), raw_text=f"/session resume {session_id}")
    assert resumed.ok is False
    assert resumed.mode == "session_resume"
    assert "不可 resume" in resumed.payload["error"]


def test_session_list_marks_rolled_back_session_not_resumable(tmp_path):
    (tmp_path / "README.md").write_text("before\n", encoding="utf-8")
    created = create_task_session(str(tmp_path), create_workspace=True)
    session_id = created["session_id"]

    service = CLIChatService()
    service.handle_input(repo_root=str(tmp_path), raw_text=f"/rollback {session_id}")

    listed = service.handle_input(repo_root=str(tmp_path), raw_text="/session list")
    target = next(item for item in listed.payload["sessions"] if item["session_id"] == session_id)
    assert target["status"] == "rolled_back"
    assert target["resumable"] is False
