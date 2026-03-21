import json

from repo_guardian_mcp.cli import main


def test_cli_chat_once_run_uses_canonical_trace_text(tmp_path, capsys):
    (tmp_path / "README.md").write_text("demo\n", encoding="utf-8")
    code = main(["chat", str(tmp_path), "--message", "請分析這個專案", "--once"])
    captured = capsys.readouterr()

    assert code == 0
    data = json.loads(captured.out)
    assert data["trace_summary_text"] == data["trace_summary"]["text"]
    assert data["display_message"].endswith(data["trace_summary"]["text"])
    assert "選擇 技能" not in data["trace_summary_text"]
    assert "驗證 結果" not in data["trace_summary_text"]


def test_cli_chat_once_status_uses_canonical_trace_text(tmp_path, capsys):
    (tmp_path / "README.md").write_text("demo\n", encoding="utf-8")
    code = main(["chat", str(tmp_path), "--message", "/status", "--once"])
    captured = capsys.readouterr()

    assert code == 0
    data = json.loads(captured.out)
    assert data["trace_summary_text"] == data["trace_summary"]["text"]
    assert data["display_message"].endswith(data["trace_summary"]["text"])
    assert "沒 有" not in data["trace_summary"]["text"]
