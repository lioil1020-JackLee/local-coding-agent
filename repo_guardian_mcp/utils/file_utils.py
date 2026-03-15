from __future__ import annotations

from pathlib import Path


def read_file_safe(path: Path) -> str:
    """
    安全讀取整個檔案內容。
    """
    if not path.exists():
        raise FileNotFoundError(f"檔案不存在: {path}")

    if not path.is_file():
        raise ValueError(f"不是檔案: {path}")

    return path.read_text(encoding="utf-8", errors="ignore")


def read_file_region(path: Path, start_line: int, end_line: int) -> str:
    """
    讀取檔案的部分區段。
    """
    content = read_file_safe(path)
    lines = content.splitlines()

    start = max(start_line - 1, 0)
    end = min(end_line, len(lines))

    return "\n".join(lines[start:end])


def write_file_safe(path: Path, content: str) -> None:
    """
    安全寫入檔案內容。
    """
    path.parent.mkdir(parents=True, exist_ok=True)

    path.write_text(content, encoding="utf-8")