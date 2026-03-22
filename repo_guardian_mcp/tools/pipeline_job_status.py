from __future__ import annotations

from repo_guardian_mcp.services.pipeline_background_service import PipelineBackgroundService


def pipeline_job_status(repo_root: str, job_id: str) -> dict:
    service = PipelineBackgroundService()
    return service.status(repo_root=repo_root, job_id=job_id)


def pipeline_job_list(repo_root: str, limit: int = 20) -> dict:
    service = PipelineBackgroundService()
    return service.list(repo_root=repo_root, limit=limit)
