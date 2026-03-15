from __future__ import annotations

from typing import Any

from repo_guardian_mcp.models import ProposePatchRequest
from repo_guardian_mcp.services.patch_service import (
    PatchModelError,
    PatchPolicyError,
    PatchService,
    PatchServiceError,
)


def propose_patch(
    task: str,
    relevant_paths: list[str] | None = None,
    readonly_paths: list[str] | None = None,
    context_snippets: list[str] | None = None,
    impact_summary: str | None = None,
    constraints: list[str] | None = None,
    max_files_to_change: int = 5,
    require_tests: bool = True,
    allow_new_files: bool = True,
    repo_root: str | None = None,
) -> dict[str, Any]:
    """
    Generate a structured patch proposal for a coding task.

    This tool does not modify the workspace. It only returns a patch plan.
    """

    try:
        req = ProposePatchRequest(
            task=task,
            repo_root=repo_root,
            relevant_paths=relevant_paths or [],
            readonly_paths=readonly_paths or [],
            context_snippets=context_snippets or [],
            impact_summary=impact_summary,
            constraints=constraints or [],
            max_files_to_change=max_files_to_change,
            require_tests=require_tests,
            allow_new_files=allow_new_files,
        )
    except Exception as exc:
        return {
            "ok": False,
            "error_type": "invalid_request",
            "message": f"Invalid propose_patch request: {exc}",
        }

    service = PatchService()

    try:
        resp = service.propose_patch(req)
        return {
            "ok": True,
            "result": resp.model_dump(mode="json"),
        }

    except PatchPolicyError as exc:
        return {
            "ok": False,
            "error_type": "patch_policy_error",
            "message": str(exc),
        }

    except PatchModelError as exc:
        return {
            "ok": False,
            "error_type": "patch_model_error",
            "message": str(exc),
        }

    except PatchServiceError as exc:
        return {
            "ok": False,
            "error_type": "patch_service_error",
            "message": str(exc),
        }

    except Exception as exc:
        return {
            "ok": False,
            "error_type": "unexpected_error",
            "message": f"Unexpected error in propose_patch: {exc}",
        }