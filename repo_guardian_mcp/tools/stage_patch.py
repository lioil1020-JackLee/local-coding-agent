from __future__ import annotations

"""
stage_patch 工具

將模型產生的 patch 實際套用到工作目錄。此工具會寫入檔案，
並回傳被觸及的檔案清單。請確保已做好版本控制或在 sandbox 下執行。
"""

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
    """套用 patch 並寫入檔案。"""
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