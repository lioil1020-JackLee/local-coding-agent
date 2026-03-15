from __future__ import annotations

from pathlib import Path
from typing import Any

from repo_guardian_mcp.models import ProposePatchResponse
from repo_guardian_mcp.services.diff_service import DiffService, DiffServiceError


class StagingServiceError(Exception):
    """Base exception for staging errors."""


class StageApplyError(StagingServiceError):
    """Raised when a patch cannot be staged into the workspace."""


class StagingService:
    def __init__(self, repo_root: str | Path) -> None:
        self.repo_root = Path(repo_root).resolve()
        self.diff_service = DiffService(repo_root=self.repo_root)

    def stage_patch(self, patch: ProposePatchResponse) -> dict[str, Any]:
        per_file_ops = self._group_operations_by_file(patch)

        touched_files: list[str] = []
        created_files: list[str] = []
        updated_files: list[str] = []

        for rel_path, ops in per_file_ops.items():
            abs_path = self.repo_root / rel_path
            file_existed_before = abs_path.exists()

            try:
                original_text = self._read_file_if_exists(abs_path)
                updated_text = self.diff_service._apply_operations(
                    original_text,
                    ops,
                    rel_path,
                )
            except DiffServiceError as exc:
                raise StageApplyError(
                    f"Failed to apply patch operations for {rel_path}: {exc}"
                ) from exc
            except Exception as exc:
                raise StageApplyError(
                    f"Unexpected staging failure for {rel_path}: {exc}"
                ) from exc

            self._ensure_parent_dir(abs_path)
            abs_path.write_text(updated_text, encoding="utf-8")

            touched_files.append(rel_path)

            if not file_existed_before:
                created_files.append(rel_path)
            else:
                updated_files.append(rel_path)

        return {
            "success": True,
            "summary": patch.summary,
            "touched_files": sorted(touched_files),
            "created_files": sorted(created_files),
            "updated_files": sorted(updated_files),
        }

    @staticmethod
    def _group_operations_by_file(
        patch: ProposePatchResponse,
    ) -> dict[str, list]:
        per_file_ops: dict[str, list] = {}
        for op in patch.operations:
            per_file_ops.setdefault(op.target.path, []).append(op)
        return per_file_ops

    @staticmethod
    def _read_file_if_exists(path: Path) -> str:
        if not path.exists():
            return ""
        return path.read_text(encoding="utf-8")

    @staticmethod
    def _ensure_parent_dir(path: Path) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)