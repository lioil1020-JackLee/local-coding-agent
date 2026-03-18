from __future__ import annotations

"""
sandbox_edit_service 提供對 sandbox 檔案進行基本文字編輯的能力。

設計重點：
- append 採 append_if_missing
- replace 採 replace_once，且具有基本 idempotent 行為
- 不支援其他模式
"""

from pathlib import Path
from typing import Any


class EditConflictError(ValueError):
    """表示指定的文字無法安全套用。"""


class UnsupportedEditModeError(ValueError):
    """表示收到不支援的修改模式。"""


def _normalize_append_text(original_text: str, content: str) -> str:
    if original_text.endswith("\n") or not original_text:
        return original_text + content
    return original_text + "\n" + content


def apply_text_edit(
    sandbox_path: str | Path,
    relative_path: str,
    content: str,
    mode: str = "append",
    old_text: str | None = None,
) -> str:
    """
    在 sandbox 指定檔案做單一文字修改。

    設計重點：
    - append 採 append_if_missing
    - replace 採 replace_once
    - replace 具備最基本 idempotent 行為
    """

    if not relative_path or not relative_path.strip():
        raise ValueError("relative_path 不能為空")

    if not content:
        raise ValueError("content 不能為空")

    sandbox_root = Path(sandbox_path).resolve()
    target_path = sandbox_root / relative_path

    if not target_path.exists():
        raise ValueError(f"找不到檔案: {target_path}")

    text = target_path.read_text(encoding="utf-8")

    if mode == "append":
        if content in text:
            return str(target_path)

        target_path.write_text(_normalize_append_text(text, content), encoding="utf-8")
        return str(target_path)

    if mode == "replace":
        if not old_text:
            raise ValueError("mode=replace 時 old_text 不能為空")

        if old_text in text:
            target_path.write_text(text.replace(old_text, content, 1), encoding="utf-8")
            return str(target_path)

        # idempotent replace: 舊字串不存在，但新字串已存在，視為已完成。
        if content in text:
            return str(target_path)

        raise ValueError(f"找不到要替換的文字: {old_text}")

    raise UnsupportedEditModeError(f"不支援的 mode: {mode}")


def apply_text_operations(
    sandbox_path: str | Path,
    operations: list[dict[str, Any]],
) -> list[str]:
    if not operations:
        raise ValueError("operations 不能為空")

    edited_files: list[str] = []

    for op in operations:
        if not isinstance(op, dict):
            raise ValueError("operations 內每個項目都必須是 dict")

        edited_file = apply_text_edit(
            sandbox_path=sandbox_path,
            relative_path=op.get("relative_path"),
            content=op.get("content"),
            mode=op.get("mode", "append"),
            old_text=op.get("old_text"),
        )

        if edited_file not in edited_files:
            edited_files.append(edited_file)

    return edited_files