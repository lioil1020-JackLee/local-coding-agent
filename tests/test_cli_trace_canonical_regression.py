import json

from repo_guardian_mcp.cli import main


def test_cli_chat_once_trace_fields_are_canonicalized(tmp_path, capsys):
    (tmp_path / "README.md").write_text("demo\n", encoding="utf-8")
    code = main(["chat", str(tmp_path), "--message", "請分析這個專案", "--once"])
    captured = capsys.readouterr()
    assert code == 0
    data = json.loads(captured.out)

    assert data["trace_summary"]["text"] == data["trace_summary_text"]
    assert data["display_message"] == "已執行 repo 分析並寫入 session。\n\n" + data["trace_summary_text"]
    assert "成 功" not in data["trace_summary"]["text"]
    assert "驗證 結果" not in data["trace_summary"]["text"]
    assert "-  驗證結果" not in data["trace_summary_text"]


def test_cli_chat_once_trace_fields_are_canonicalized_with_user_prompt(tmp_path, capsys):
    (tmp_path / "README.md").write_text("demo\n", encoding="utf-8")
    code = main(
        [
            "chat",
            str(tmp_path),
            "--message",
            "請分析 trace summary 的輸出格式 ，不要修改任何檔案",
            "--once",
        ]
    )
    captured = capsys.readouterr()
    assert code == 0
    data = json.loads(captured.out)

    assert data["trace_summary"]["text"] == data["trace_summary_text"]
    assert data["display_message"] == "已執行 repo 分析並寫入 session。\n\n" + data["trace_summary_text"]
    assert "成 功" not in data["display_message"]
    assert "驗證 結果" not in data["display_message"]
