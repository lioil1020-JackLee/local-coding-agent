import json

from repo_guardian_mcp.cli import main


def test_cli_bridge_invoke_status_trace(tmp_path, capsys):
    (tmp_path / "README.md").write_text("demo\n", encoding="utf-8")

    code = main(
        [
            "bridge",
            "invoke",
            str(tmp_path),
            "--prompt",
            "請先幫我分析專案入口，先不要修改檔案",
            "--task-type",
            "analyze",
        ]
    )
    captured = capsys.readouterr()
    assert code == 0
    invoke_data = json.loads(captured.out)
    assert invoke_data["ok"] is True
    task_id = invoke_data["task_id"]
    session_id = invoke_data["session_id"]

    code = main(["bridge", "status", str(tmp_path), task_id])
    captured = capsys.readouterr()
    assert code == 0
    status_data = json.loads(captured.out)
    assert status_data["ok"] is True
    assert status_data["task_id"] == task_id
    assert status_data["status"] in {"completed", "failed", "running", "pending", "unknown"}

    code = main(["bridge", "trace", str(tmp_path), task_id])
    captured = capsys.readouterr()
    assert code == 0
    trace_data = json.loads(captured.out)
    assert trace_data["ok"] is True
    assert trace_data["trace_summary"]
    assert "trace summary" in trace_data["trace_summary_text"]

    if session_id:
        # analyze skill typically has no session_id; keep this branch for edit flows.
        code = main(["bridge", "diff", str(tmp_path), session_id])
        captured = capsys.readouterr()
        diff_data = json.loads(captured.out)
        assert code in (0, 1)
        assert "ok" in diff_data

    code = main(["bridge", "events", str(tmp_path), task_id, "--limit", "10"])
    captured = capsys.readouterr()
    assert code == 0
    events_data = json.loads(captured.out)
    assert events_data["ok"] is True
    assert events_data["mode"] == "bridge_events"
    assert events_data["count"] >= 2
    assert events_data["events"][-1]["event"] in {"trace_checked", "status_checked", "completed", "submitted"}
    assert "seq" in events_data["events"][-1]
    assert events_data["events"][-1]["level"] in {"info", "error"}

    code = main(["bridge", "diagnose", str(tmp_path), task_id])
    captured = capsys.readouterr()
    assert code == 0
    diagnose_data = json.loads(captured.out)
    assert diagnose_data["ok"] is True
    assert diagnose_data["mode"] == "bridge_diagnose"
    assert "diagnosis" in diagnose_data
    assert "plain_summary" in diagnose_data
    assert isinstance(diagnose_data["plain_summary"], str)
    assert diagnose_data["plain_summary"]
    assert "next_say_examples" in diagnose_data
    assert isinstance(diagnose_data["next_say_examples"], list)
    assert len(diagnose_data["next_say_examples"]) >= 1
    assert "recommended_next_commands" in diagnose_data
    assert isinstance(diagnose_data["recommended_next_commands"], list)
    assert len(diagnose_data["recommended_next_commands"]) >= 1
    if diagnose_data.get("diagnosis"):
        assert "recommended_commands" in diagnose_data["diagnosis"]

    code = main(["bridge", "list", str(tmp_path), "--limit", "5"])
    captured = capsys.readouterr()
    assert code == 0
    list_data = json.loads(captured.out)
    assert list_data["ok"] is True
    assert list_data["mode"] == "bridge_list"
    assert list_data["count"] >= 1
    assert list_data["tasks"][0]["bridge_status"] in {"completed", "failed", "running", "pending", "unknown"}
    assert "latency_ms" in list_data["tasks"][0]

    code = main(["bridge", "latest", str(tmp_path)])
    captured = capsys.readouterr()
    assert code == 0
    latest_data = json.loads(captured.out)
    assert latest_data["ok"] is True
    assert latest_data["mode"] == "bridge_latest"
    assert latest_data["latest_task"]["task_id"] == task_id
    assert latest_data["diagnosis"]["ok"] is True

    code = main(["bridge", "cleanup", str(tmp_path), "--days", "0", "--keep", "1", "--dry-run"])
    captured = capsys.readouterr()
    assert code == 0
    cleanup_data = json.loads(captured.out)
    assert cleanup_data["ok"] is True
    assert cleanup_data["mode"] == "bridge_cleanup"
    assert cleanup_data["dry_run"] is True

    code = main(["bridge", "queue", str(tmp_path), "--limit", "10"])
    captured = capsys.readouterr()
    assert code == 0
    queue_data = json.loads(captured.out)
    assert queue_data["ok"] is True
    assert queue_data["mode"] == "bridge_queue"
    assert "counts" in queue_data
    assert "completed" in queue_data["counts"]
    assert "diagnosis_counts" in queue_data
