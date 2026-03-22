from __future__ import annotations

import argparse
from typing import Any

from repo_guardian_mcp.services.pipeline_background_service import PipelineBackgroundService
from repo_guardian_mcp.tools.run_task_pipeline import run_task_pipeline


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run repo_guardian task pipeline in background.")
    parser.add_argument("--repo-root", required=True)
    parser.add_argument("--job-id", required=True)
    return parser.parse_args()


def main() -> int:
    args = _parse_args()
    service = PipelineBackgroundService()
    repo_root = str(args.repo_root)
    job_id = str(args.job_id)
    status = service.status(repo_root=repo_root, job_id=job_id)
    if not status.get("ok"):
        return 1

    payload: dict[str, Any] = dict((status.get("payload") or {}))
    service.mark_running(repo_root=repo_root, job_id=job_id)
    try:
        result = run_task_pipeline(
            repo_root=repo_root,
            relative_path=str(payload.get("relative_path") or "README.md"),
            content=str(payload.get("content") or ""),
            mode=str(payload.get("mode") or "append"),
            old_text=payload.get("old_text"),
            operations=payload.get("operations"),
            task_type=str(payload.get("task_type") or "auto"),
            user_request=str(payload.get("user_request") or ""),
            session_id=payload.get("session_id"),
            metadata=payload.get("metadata"),
            auto_decompose=bool(payload.get("auto_decompose", True)),
            pipeline_id=payload.get("pipeline_id"),
            resume=bool(payload.get("resume", True)),
            max_retries_per_step=int(payload.get("max_retries_per_step") or 1),
            background=False,
        )
        service.mark_done(repo_root=repo_root, job_id=job_id, result=result)
        return 0 if result.get("ok") else 2
    except Exception as exc:  # noqa: BLE001
        service.mark_failed(repo_root=repo_root, job_id=job_id, error=str(exc))
        return 3


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
