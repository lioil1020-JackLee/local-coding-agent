from __future__ import annotations

from typing import Any

from repo_guardian_mcp.models import ProposePatchResponse
from repo_guardian_mcp.services.staging_service import (
    StageApplyError,
    StagingService,
)


def stage_patch(
    patch: dict[str, Any],
    repo_root: str = ".",
) -> dict[str, Any]:
    """
    Apply a structured patch proposal to the workspace.

    This writes the modified files to disk.
    """

    try:
        parsed_patch = ProposePatchResponse.model_validate(patch)
    except Exception as exc:
        return {
            "ok": False,
            "error_type": "invalid_patch_payload",
            "message": f"Invalid patch payload: {exc}",
        }

    try:
        service = StagingService(repo_root=repo_root)

        result = service.stage_patch(parsed_patch)

        return {
            "ok": True,
            "result": result,
        }

    except StageApplyError as exc:
        return {
            "ok": False,
            "error_type": "stage_apply_error",
            "message": str(exc),
        }

    except Exception as exc:
        return {
            "ok": False,
            "error_type": "unexpected_error",
            "message": f"Unexpected stage_patch failure: {exc}",
        }