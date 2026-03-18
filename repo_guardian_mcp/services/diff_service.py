from __future__ import annotations

"""
diff_service

這個服務負責在記憶體中套用 patch 操作並產生 unified diff。

目前僅支援 create_file、replace_range 與 insert_at 三種操作類型，
delete_file 為安全考量尚未啟用。
"""

import difflib
from pathlib import Path

from repo_guardian_mcp.models import (
    PatchAnchorMode,
    PatchOperation,
    PatchOperationType,
    ProposePatchResponse,
)


class DiffServiceError(Exception):
    """基礎的 diff 產生錯誤。"""


class DiffApplyError(DiffServiceError):
    """當無法應用某個 patch 操作時拋出。"""


class DiffService:
    def __init__(self, repo_root: str | Path) -> None:
        self.repo_root = Path(repo_root).resolve()

    def build_unified_diff(self, patch: ProposePatchResponse) -> str:
        """將 patch 中的所有操作套用在各檔案內容上並產生 unified diff。"""
        # 將操作依檔案分組
        per_file_ops: dict[str, list[PatchOperation]] = {}
        for op in patch.operations:
            per_file_ops.setdefault(op.target.path, []).append(op)
        all_diffs: list[str] = []
        for rel_path, ops in per_file_ops.items():
            original_text = self._read_file_if_exists(rel_path)
            updated_text = self._apply_operations(original_text, ops, rel_path)
            old_lines = self._to_lines(original_text)
            new_lines = self._to_lines(updated_text)
            diff_lines = list(
                difflib.unified_diff(
                    old_lines,
                    new_lines,
                    fromfile=f"a/{rel_path}",
                    tofile=f"b/{rel_path}",
                    lineterm="",
                )
            )
            if diff_lines:
                all_diffs.append("\n".join(diff_lines))
        return "\n\n".join(all_diffs)

    def _read_file_if_exists(self, rel_path: str) -> str:
        path = self.repo_root / rel_path
        if not path.exists():
            return ""
        return path.read_text(encoding="utf-8")

    def _apply_operations(
        self,
        original_text: str,
        ops: list[PatchOperation],
        rel_path: str,
    ) -> str:
        current = original_text
        for op in ops:
            current = self._apply_single_operation(current, op, rel_path)
        return current

    def _apply_single_operation(
        self,
        text: str,
        op: PatchOperation,
        rel_path: str,
    ) -> str:
        if op.type == PatchOperationType.CREATE_FILE:
            if text:
                raise DiffApplyError(f"create_file target already exists: {rel_path}")
            return op.content or ""
        if op.type == PatchOperationType.REPLACE_RANGE:
            return self._apply_replace_range(text, op, rel_path)
        if op.type == PatchOperationType.INSERT_AT:
            return self._apply_insert_at(text, op, rel_path)
        if op.type == PatchOperationType.DELETE_FILE:
            raise DiffApplyError("delete_file is not supported in diff preview v1")
        raise DiffApplyError(f"Unsupported operation type: {op.type}")

    def _apply_replace_range(
        self,
        text: str,
        op: PatchOperation,
        rel_path: str,
    ) -> str:
        if op.range is None:
            raise DiffApplyError(f"replace_range missing range: {rel_path}")
        if op.range.mode == PatchAnchorMode.LINE:
            if op.range.start_line is None or op.range.end_line is None:
                raise DiffApplyError(f"replace_range line anchors incomplete: {rel_path}")
            lines = text.splitlines(keepends=True)
            start_idx = op.range.start_line - 1
            end_idx = op.range.end_line
            if start_idx < 0 or end_idx > len(lines) or start_idx > end_idx:
                raise DiffApplyError(
                    f"replace_range line anchors out of bounds for {rel_path}: {op.range.start_line}-{op.range.end_line}"
                )
            new_chunk = self._normalize_content_to_lines(op.content or "")
            replaced = lines[:start_idx] + new_chunk + lines[end_idx:]
            return "".join(replaced)
        if op.range.mode == PatchAnchorMode.TEXT:
            if not op.range.start_text or not op.range.end_text:
                raise DiffApplyError(f"replace_range text anchors incomplete: {rel_path}")
            start_pos = text.find(op.range.start_text)
            if start_pos == -1:
                raise DiffApplyError(
                    f"replace_range start_text not found in {rel_path}: {op.range.start_text!r}"
                )
            end_anchor_pos = text.find(op.range.end_text, start_pos)
            if end_anchor_pos == -1:
                raise DiffApplyError(
                    f"replace_range end_text not found in {rel_path}: {op.range.end_text!r}"
                )
            end_pos = end_anchor_pos + len(op.range.end_text)
            return text[:start_pos] + (op.content or "") + text[end_pos:]
        raise DiffApplyError(f"Unsupported replace_range mode in {rel_path}: {op.range.mode}")

    def _apply_insert_at(
        self,
        text: str,
        op: PatchOperation,
        rel_path: str,
    ) -> str:
        if op.insert_at is None:
            raise DiffApplyError(f"insert_at missing anchor: {rel_path}")
        content = op.content or ""
        if op.insert_at.mode == PatchAnchorMode.LINE:
            if op.insert_at.line is None:
                raise DiffApplyError(f"insert_at line anchor missing line: {rel_path}")
            lines = text.splitlines(keepends=True)
            line_idx = op.insert_at.line - 1
            if line_idx < 0 or line_idx > len(lines):
                raise DiffApplyError(
                    f"insert_at line anchor out of bounds for {rel_path}: {op.insert_at.line}"
                )
            insert_lines = self._normalize_content_to_lines(content)
            if op.insert_at.position == "before":
                updated = lines[:line_idx] + insert_lines + lines[line_idx:]
            else:
                updated = lines[: line_idx + 1] + insert_lines + lines[line_idx + 1 :]
            return "".join(updated)
        if op.insert_at.mode == PatchAnchorMode.TEXT:
            if not op.insert_at.text:
                raise DiffApplyError(f"insert_at text anchor missing text: {rel_path}")
            anchor = op.insert_at.text
            anchor_pos = text.find(anchor)
            if anchor_pos == -1:
                raise DiffApplyError(
                    f"insert_at text anchor not found in {rel_path}: {anchor!r}"
                )
            if op.insert_at.position == "before":
                insert_pos = anchor_pos
            else:
                insert_pos = anchor_pos + len(anchor)
            return text[:insert_pos] + content + text[insert_pos:]
        raise DiffApplyError(f"Unsupported insert_at mode in {rel_path}: {op.insert_at.mode}")

    @staticmethod
    def _normalize_content_to_lines(content: str) -> list[str]:
        return content.splitlines(keepends=True)

    @staticmethod
    def _to_lines(text: str) -> list[str]:
        return text.splitlines(keepends=True)