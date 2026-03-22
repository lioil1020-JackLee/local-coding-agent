from __future__ import annotations

from pathlib import Path

from repo_guardian_mcp.services.pipeline_background_service import PipelineBackgroundService


def test_pipeline_background_submit_and_status(tmp_path: Path, monkeypatch) -> None:
    service = PipelineBackgroundService()

    calls: list[tuple[str, str]] = []

    def _fake_spawn(*, repo_root: str, job_id: str) -> None:
        calls.append((repo_root, job_id))

    monkeypatch.setattr(service, "_spawn_worker", _fake_spawn)

    queued = service.submit(
        repo_root=str(tmp_path),
        payload={"task_type": "auto", "user_request": "請分析整個專案"},
    )
    assert queued["ok"] is True
    assert queued["status"] == "queued"
    assert calls and calls[0][1] == queued["job_id"]

    status = service.status(repo_root=str(tmp_path), job_id=queued["job_id"])
    assert status["ok"] is True
    assert status["status"] == "queued"
    assert status["payload"]["task_type"] == "auto"


def test_pipeline_background_list_jobs(tmp_path: Path, monkeypatch) -> None:
    service = PipelineBackgroundService()
    monkeypatch.setattr(service, "_spawn_worker", lambda **_: None)
    a = service.submit(repo_root=str(tmp_path), payload={"task_type": "auto"})
    b = service.submit(repo_root=str(tmp_path), payload={"task_type": "analyze"})

    listed = service.list(repo_root=str(tmp_path), limit=10)
    assert listed["ok"] is True
    ids = [row["job_id"] for row in listed["jobs"]]
    assert a["job_id"] in ids
    assert b["job_id"] in ids
