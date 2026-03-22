import json

from repo_guardian_mcp.cli import main


def test_observe_routing_cli(tmp_path, capsys):
    (tmp_path / "README.md").write_text("demo\n", encoding="utf-8")
    main(["chat", str(tmp_path), "--message", "請分析這個專案", "--once"])
    capsys.readouterr()

    code = main(["observe", "routing", str(tmp_path)])
    captured = capsys.readouterr()

    assert code == 0
    data = json.loads(captured.out)
    assert data["ok"] is True
    assert data["mode"] == "observe_routing"
    assert "routing_observability" in data

