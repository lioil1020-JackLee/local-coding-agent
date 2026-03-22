from __future__ import annotations

import json
import subprocess
import sys
import time
import uuid
from pathlib import Path
from typing import Any


class PipelineBackgroundService:
    """管理背景 pipeline 任務（提交、查詢、完成回寫）。"""

    def _jobs_dir(self, repo_root: str) -> Path:
        path = Path(repo_root).resolve() / "agent_runtime" / "pipeline_jobs"
        path.mkdir(parents=True, exist_ok=True)
        return path

    def _job_file(self, repo_root: str, job_id: str) -> Path:
        return self._jobs_dir(repo_root) / f"{job_id}.json"

    def submit(self, *, repo_root: str, payload: dict[str, Any]) -> dict[str, Any]:
        job_id = f"job-{uuid.uuid4().hex[:12]}"
        now = int(time.time() * 1000)
        job = {
            "job_id": job_id,
            "status": "queued",
            "repo_root": str(Path(repo_root).resolve()),
            "created_at_ms": now,
            "updated_at_ms": now,
            "payload": dict(payload or {}),
            "result": None,
            "error": None,
        }
        self._save(repo_root=repo_root, job_id=job_id, job=job)
        self._spawn_worker(repo_root=repo_root, job_id=job_id)
        return {
            "ok": True,
            "job_id": job_id,
            "status": "queued",
            "job_file": str(self._job_file(repo_root, job_id)),
        }

    def mark_running(self, *, repo_root: str, job_id: str) -> None:
        job = self._load(repo_root=repo_root, job_id=job_id)
        if not job:
            return
        job["status"] = "running"
        job["updated_at_ms"] = int(time.time() * 1000)
        self._save(repo_root=repo_root, job_id=job_id, job=job)

    def mark_done(self, *, repo_root: str, job_id: str, result: dict[str, Any]) -> None:
        job = self._load(repo_root=repo_root, job_id=job_id)
        if not job:
            return
        job["status"] = "completed" if bool(result.get("ok")) else "failed"
        job["result"] = result
        job["error"] = None if result.get("ok") else result.get("error")
        job["updated_at_ms"] = int(time.time() * 1000)
        self._save(repo_root=repo_root, job_id=job_id, job=job)

    def mark_failed(self, *, repo_root: str, job_id: str, error: str) -> None:
        job = self._load(repo_root=repo_root, job_id=job_id)
        if not job:
            return
        job["status"] = "failed"
        job["error"] = str(error)
        job["updated_at_ms"] = int(time.time() * 1000)
        self._save(repo_root=repo_root, job_id=job_id, job=job)

    def status(self, *, repo_root: str, job_id: str) -> dict[str, Any]:
        job = self._load(repo_root=repo_root, job_id=job_id)
        if not job:
            return {"ok": False, "error": f"job '{job_id}' not found"}
        return {"ok": True, **job}

    def list(self, *, repo_root: str, limit: int = 20) -> dict[str, Any]:
        rows: list[dict[str, Any]] = []
        for path in sorted(self._jobs_dir(repo_root).glob("job-*.json"), key=lambda p: p.stat().st_mtime, reverse=True):
            try:
                payload = json.loads(path.read_text(encoding="utf-8"))
            except Exception:
                continue
            rows.append(
                {
                    "job_id": payload.get("job_id"),
                    "status": payload.get("status"),
                    "created_at_ms": payload.get("created_at_ms"),
                    "updated_at_ms": payload.get("updated_at_ms"),
                    "error": payload.get("error"),
                }
            )
            if limit > 0 and len(rows) >= limit:
                break
        return {"ok": True, "count": len(rows), "jobs": rows}

    def _load(self, *, repo_root: str, job_id: str) -> dict[str, Any] | None:
        path = self._job_file(repo_root, job_id)
        if not path.exists():
            return None
        try:
            return json.loads(path.read_text(encoding="utf-8"))
        except Exception:
            return None

    def _save(self, *, repo_root: str, job_id: str, job: dict[str, Any]) -> None:
        path = self._job_file(repo_root, job_id)
        path.write_text(json.dumps(job, ensure_ascii=False, indent=2), encoding="utf-8")

    def _spawn_worker(self, *, repo_root: str, job_id: str) -> None:
        cmd = [
            sys.executable,
            "-m",
            "repo_guardian_mcp.workers.pipeline_background_worker",
            "--repo-root",
            str(Path(repo_root).resolve()),
            "--job-id",
            job_id,
        ]
        kwargs: dict[str, Any] = {
            "cwd": str(Path(repo_root).resolve()),
            "stdout": subprocess.DEVNULL,
            "stderr": subprocess.DEVNULL,
        }
        if sys.platform.startswith("win"):
            kwargs["creationflags"] = subprocess.CREATE_NEW_PROCESS_GROUP | subprocess.DETACHED_PROCESS  # type: ignore[attr-defined]
        else:
            kwargs["start_new_session"] = True
        subprocess.Popen(cmd, **kwargs)  # noqa: S603
