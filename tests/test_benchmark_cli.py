import json

from repo_guardian_mcp.cli import main


def test_benchmark_init(tmp_path, capsys):
    code = main(["benchmark", "init", str(tmp_path)])
    captured = capsys.readouterr()
    assert code == 0
    data = json.loads(captured.out)
    assert data["ok"] is True
    assert data["mode"] == "benchmark_init"
    assert "corpus_file" in data


def test_benchmark_run_and_report(tmp_path, capsys):
    (tmp_path / "README.md").write_text("demo\n", encoding="utf-8")

    code = main(["benchmark", "run", str(tmp_path), "--threshold", "0.5"])
    captured = capsys.readouterr()
    assert code == 0
    run_data = json.loads(captured.out)
    assert run_data["ok"] is True
    assert run_data["mode"] == "benchmark_run"
    assert run_data["total"] >= 1
    assert run_data["success_rate"] >= 0.5
    assert run_data["routing_observability"]["total_results"] == run_data["total"]
    assert run_data["corpus"]["name"] in {"core-zh-tw-local-agent", "legacy-fixed-tasks", "custom-corpus"}

    code = main(["benchmark", "report", str(tmp_path)])
    captured = capsys.readouterr()
    assert code == 0
    report_data = json.loads(captured.out)
    assert report_data["ok"] is True
    assert report_data["mode"] == "benchmark_report"
    assert report_data["session_observability"] is not None


def test_benchmark_run_with_custom_tasks_file(tmp_path, capsys):
    (tmp_path / "README.md").write_text("demo\n", encoding="utf-8")
    custom = tmp_path / "custom_tasks.json"
    custom.write_text(
        json.dumps(
            {
                "version": "1.0",
                "name": "custom",
                "tasks": [
                    {
                        "name": "a1",
                        "task_type": "analyze",
                        "user_request": "請分析專案重點",
                    }
                ],
            },
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )

    code = main(["benchmark", "run", str(tmp_path), "--tasks-file", str(custom), "--threshold", "0.5"])
    captured = capsys.readouterr()
    assert code == 0
    data = json.loads(captured.out)
    assert data["ok"] is True
    assert data["corpus"]["name"] == "custom"
