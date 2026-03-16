from __future__ import annotations

from pathlib import Path
from typing import Any


def apply_text_edit(
    sandbox_path: str | Path,
    relative_path: str,
    content: str,
    mode: str = "append",
    old_text: str | None = None,
) -> str:
    """
    在 sandbox 指定檔案做單一文字修改
    """

    if not relative_path or not relative_path.strip():
        raise ValueError("relative_path 不能為空")

    if not content:
        raise ValueError("content 不能為空")

    sandbox_path = Path(sandbox_path).resolve()
    target_path = sandbox_path / relative_path

    if not target_path.exists():
        raise ValueError(f"找不到檔案: {target_path}")

    text = target_path.read_text(encoding="utf-8")

    if mode == "append":
        if content not in text:
            if text.endswith("\n"):
                new_text = text + content
            else:
                new_text = text + "\n" + content

            target_path.write_text(new_text, encoding="utf-8")

        return str(target_path)

    if mode == "replace":

        if not old_text:
            raise ValueError("mode=replace 時 old_text 不能為空")

        if old_text not in text:
            raise ValueError(f"找不到要替換的文字: {old_text}")

        new_text = text.replace(old_text, content, 1)
        target_path.write_text(new_text, encoding="utf-8")

        return str(target_path)

    raise ValueError(f"不支援的 mode: {mode}")


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

        relative_path = op.get("relative_path")
        content = op.get("content")
        mode = op.get("mode", "append")
        old_text = op.get("old_text")

        edited_file = apply_text_edit(
            sandbox_path=sandbox_path,
            relative_path=relative_path,
            content=content,
            mode=mode,
            old_text=old_text,
        )

        if edited_file not in edited_files:
            edited_files.append(edited_file)

    return edited_files