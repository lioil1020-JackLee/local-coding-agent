import json

from repo_guardian_mcp.cli import main
from repo_guardian_mcp.services.cli_chat_service import CLIChatService


def test_chat_service_help():
    service = CLIChatService()
    result = service.handle_input(repo_root=".", raw_text="/help")
    assert result.ok is True
    assert result.mode == "help"
    assert "/run <text>" in result.message


def test_cli_chat_once_message(tmp_path, capsys):
    (tmp_path / "README.md").write_text("demo\n", encoding="utf-8")
    code = main(["chat", str(tmp_path), "--message", "請分析這個專案", "--once"])
    captured = capsys.readouterr()
    assert code == 0
    data = json.loads(captured.out)
    assert data["ok"] is True
    assert data["mode"] == "run"
    assert data["selected_skill"] == "analyze_repo"



def test_cli_chat_once_plan_message_with_analysis_status_phrase(tmp_path, capsys):
    (tmp_path / "README.md").write_text("demo\n", encoding="utf-8")
    code = main(["chat", str(tmp_path), "--message", "/plan 幫我分析目前專案狀態", "--once"])
    captured = capsys.readouterr()
    assert code == 0
    data = json.loads(captured.out)
    assert data["ok"] is True
    assert data["mode"] == "plan"
    assert data["selected_skill"] == "analyze_repo"


def test_cli_chat_once_status_includes_normalized_display_message(tmp_path, capsys):
    (tmp_path / "README.md").write_text("demo\n", encoding="utf-8")
    main(["chat", str(tmp_path), "--message", "請分析這個專案", "--once"])
    capsys.readouterr()

    code = main(["chat", str(tmp_path), "--message", "/status", "--once"])
    captured = capsys.readouterr()
    assert code == 0
    data = json.loads(captured.out)
    assert data["display_message"] == "已整理目前 agent session 狀態。\n\n" + data["trace_summary_text"]
    assert "選擇 技能" not in data["display_message"]
    assert "成 功" not in data["display_message"]
