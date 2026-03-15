from __future__ import annotations

from pathlib import Path


def resolve_workspace_root(path: str | Path) -> Path:
    """解析 workspace root，並回傳絕對路徑。"""
    p = Path(path)

    if not p.exists():
        raise FileNotFoundError(f"workspace path 不存在: {p}")

    return p.resolve()


def list_files_recursive(
    root: Path,
    extensions: tuple[str, ...] = (".py",),
) -> list[Path]:
    """遞迴列出指定副檔名的檔案（忽略常見無關資料夾）。"""

    IGNORE_DIRS = {
        ".venv",
        "venv",
        "__pycache__",
        ".git",
        "node_modules",
        "dist",
        "build",
    }

    results: list[Path] = []

    for file in root.rglob("*"):
        if any(part in IGNORE_DIRS for part in file.parts):
            continue

        if file.is_file() and file.suffix in extensions:
            results.append(file)

    return results