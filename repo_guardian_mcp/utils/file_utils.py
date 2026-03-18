from __future__ import annotations

"""
file_utils

提供安全的檔案讀取與寫入工具。

這些函式會在存取前檢查檔案是否存在，以及是否為一般檔案，
避免讀取資料夾或不存在的路徑造成錯誤。寫入時會自動建立目錄。
"""

from pathlib import Path


def read_file_safe(path: Path) -> str:
    """安全讀取整個檔案內容，若檔案不存在或不是檔案則拋出例外。"""
    if not path.exists():
        raise FileNotFoundError(f"檔案不存在: {path}")
    if not path.is_file():
        raise ValueError(f"不是檔案: {path}")
    # 以 utf-8 編碼讀取，忽略無法解碼的字元
    return path.read_text(encoding="utf-8", errors="ignore")


def read_file_region(path: Path, start_line: int, end_line: int) -> str:
    """讀取檔案指定行數區段的內容。

    會自動修正範圍超出邊界的情況。
    """
    content = read_file_safe(path)
    lines = content.splitlines()

    # 調整為 0-based 索引
    start = max(start_line - 1, 0)
    end = min(end_line, len(lines))

    return "\n".join(lines[start:end])


def write_file_safe(path: Path, content: str) -> None:
    """安全寫入檔案內容。若目錄不存在則自動建立。"""
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")