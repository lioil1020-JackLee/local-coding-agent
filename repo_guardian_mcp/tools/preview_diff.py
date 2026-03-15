from __future__ import annotations

from typing import Any

from repo_guardian_mcp.models import ProposePatchResponse
from repo_guardian_mcp.services.diff_service import DiffApplyError, DiffService, DiffServiceError


def preview_diff(
    patch: dict[str, Any],
    repo_root: str = ".",
) -> dict[str, Any]:
    """
    Preview a unified diff for a structured patch proposal.

    This tool does not modify files. It only applies the patch in memory
    and returns a unified diff string.
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
        diff_svc = DiffService(repo_root=repo_root)
        diff_text = diff_svc.build_unified_diff(parsed_patch)

        touched_files = sorted({op.target.path for op in parsed_patch.operations})

        return {
            "ok": True,
            "summary": parsed_patch.summary,
            "touched_files": touched_files,
            "diff": diff_text,
        }

    except DiffApplyError as exc:
        return {
            "ok": False,
            "error_type": "diff_apply_error",
            "message": str(exc),
        }

    except DiffServiceError as exc:
        return {
            "ok": False,
            "error_type": "diff_service_error",
            "message": str(exc),
        }

    except Exception as exc:
        return {
            "ok": False,
            "error_type": "unexpected_error",
            "message": f"Unexpected error in preview_diff: {exc}",
        }