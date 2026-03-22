from __future__ import annotations

import uuid
from pathlib import Path
from typing import Any

from repo_guardian_mcp.tools import run_task_pipeline as pipeline_module


class _FakeOrchestrator:
    def __init__(self) -> None:
        self.calls: list[dict[str, Any]] = []

    def run(self, **kwargs: Any) -> dict[str, Any]:
        self.calls.append(dict(kwargs))
        return {"ok": True, "echo_task_type": kwargs.get("task_type"), "echo_request": kwargs.get("user_request")}


class _FlakyOrchestrator:
    def __init__(self) -> None:
        self.calls: list[dict[str, Any]] = []
        self._attempts: dict[str, int] = {}

    def run(self, **kwargs: Any) -> dict[str, Any]:
        self.calls.append(dict(kwargs))
        meta = kwargs.get("metadata") or {}
        step_id = str(meta.get("pipeline_step_id") or "")
        self._attempts[step_id] = self._attempts.get(step_id, 0) + 1
        if step_id == "capabilities" and self._attempts[step_id] == 1:
            return {"ok": False, "error": "temporary failure"}
        return {"ok": True, "step_id": step_id}


class _AlwaysFailOrchestrator:
    def __init__(self) -> None:
        self.calls: list[dict[str, Any]] = []

    def run(self, **kwargs: Any) -> dict[str, Any]:
        self.calls.append(dict(kwargs))
        return {"ok": False, "error": "hard fail"}


def test_run_task_pipeline_auto_decompose_large_request(monkeypatch) -> None:
    holder: dict[str, Any] = {}

    def _factory() -> _FakeOrchestrator:
        inst = _FakeOrchestrator()
        holder["inst"] = inst
        return inst

    monkeypatch.setattr(pipeline_module, "TaskOrchestrator", _factory)

    result = pipeline_module.run_task_pipeline(
        repo_root=".",
        task_type="auto",
        user_request="請分析整個專案，並告訴我目前完成度是多少",
    )

    assert result["ok"] is True
    assert result["auto_decomposed"] is True
    assert "preference_profile" in result
    assert "quality_review" in result
    assert result["completed_steps"] >= 4
    assert len(result["step_results"]) >= 4

    inst = holder["inst"]
    assert len(inst.calls) >= 4
    assert all(call.get("task_type") == "analyze" for call in inst.calls)
    assert all(call.get("metadata", {}).get("auto_decomposed") is True for call in inst.calls)


def test_run_task_pipeline_single_run_for_small_request(monkeypatch) -> None:
    holder: dict[str, Any] = {}

    def _factory() -> _FakeOrchestrator:
        inst = _FakeOrchestrator()
        holder["inst"] = inst
        return inst

    monkeypatch.setattr(pipeline_module, "TaskOrchestrator", _factory)

    result = pipeline_module.run_task_pipeline(
        repo_root=".",
        task_type="analyze",
        user_request="看一下 main.py",
    )

    assert result["pipeline"] == "repo_guardian_task_pipeline"
    assert result.get("auto_decomposed") is None
    assert "quality_review" in result

    inst = holder["inst"]
    assert len(inst.calls) == 1
    assert inst.calls[0].get("task_type") == "analyze"


def test_run_task_pipeline_resume_from_checkpoint(tmp_path: Path, monkeypatch) -> None:
    holder: dict[str, Any] = {}

    def _factory() -> _FlakyOrchestrator:
        inst = _FlakyOrchestrator()
        holder["inst"] = inst
        return inst

    monkeypatch.setattr(pipeline_module, "TaskOrchestrator", _factory)

    pipeline_id = f"pipe-{uuid.uuid4().hex[:8]}"
    first = pipeline_module.run_task_pipeline(
        repo_root=str(tmp_path),
        task_type="auto",
        user_request="請分析整個專案並整理完成度",
        pipeline_id=pipeline_id,
        resume=True,
        max_retries_per_step=0,
    )

    assert first["ok"] is False
    assert first["failed_step_id"] == "capabilities"
    assert first["pipeline_id"] == pipeline_id

    second = pipeline_module.run_task_pipeline(
        repo_root=str(tmp_path),
        task_type="auto",
        user_request="請分析整個專案並整理完成度",
        pipeline_id=pipeline_id,
        resume=True,
        max_retries_per_step=1,
    )

    assert second["ok"] is True
    assert second["pipeline_id"] == pipeline_id
    assert second["resumed_from_checkpoint"] is True
    assert second["remaining_steps"] == 0


def test_run_task_pipeline_auto_resume_without_pipeline_id(tmp_path: Path, monkeypatch) -> None:
    holder: dict[str, Any] = {}

    def _factory() -> _FlakyOrchestrator:
        inst = _FlakyOrchestrator()
        holder["inst"] = inst
        return inst

    monkeypatch.setattr(pipeline_module, "TaskOrchestrator", _factory)

    first = pipeline_module.run_task_pipeline(
        repo_root=str(tmp_path),
        task_type="auto",
        user_request="請分析整個專案並整理完成度",
        resume=True,
        max_retries_per_step=0,
    )
    assert first["ok"] is False

    second = pipeline_module.run_task_pipeline(
        repo_root=str(tmp_path),
        task_type="auto",
        user_request="請分析整個專案並整理完成度",
        resume=True,
        max_retries_per_step=1,
    )
    assert second["ok"] is True
    assert second["resumed_from_checkpoint"] is True
    assert second["auto_resume_selected"] is True


def test_run_task_pipeline_background_mode(monkeypatch) -> None:
    class _FakeBG:
        def submit(self, *, repo_root: str, payload: dict[str, Any]) -> dict[str, Any]:
            assert payload["task_type"] == "auto"
            return {"ok": True, "job_id": "job-demo", "status": "queued", "job_file": "x"}

    monkeypatch.setattr(pipeline_module, "PipelineBackgroundService", _FakeBG)
    out = pipeline_module.run_task_pipeline(
        repo_root=".",
        task_type="auto",
        user_request="請分析整個專案",
        background=True,
    )
    assert out["ok"] is True
    assert out["background"] is True
    assert out["background_job"]["job_id"] == "job-demo"


def test_run_task_pipeline_failure_includes_alternative_actions(monkeypatch) -> None:
    def _factory() -> _AlwaysFailOrchestrator:
        return _AlwaysFailOrchestrator()

    monkeypatch.setattr(pipeline_module, "TaskOrchestrator", _factory)
    out = pipeline_module.run_task_pipeline(
        repo_root=".",
        task_type="analyze",
        user_request="請分析完成度",
    )
    assert out["ok"] is False
    assert "truthfulness_review" in out
    assert isinstance(out.get("next_actions"), list)
    assert len(out["next_actions"]) >= 1
