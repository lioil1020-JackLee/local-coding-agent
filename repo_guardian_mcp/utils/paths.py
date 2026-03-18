from __future__ import annotations

"""
paths

提供與路徑相關的輔助函式，例如解析工作目錄與遞迴列出檔案。
"""

from pathlib import Path


def resolve_workspace_root(path: str | Path) -> Path:
    """解析 workspace 根目錄並回傳絕對路徑。

    若路徑不存在，則拋出 FileNotFoundError。"""
    p = Path(path)
    if not p.exists():
        raise FileNotFoundError(f"workspace path 不存在: {p}")
    return p.resolve()


def list_files_recursive(
    root: Path, extensions: tuple[str, ...] = (".py",)
) -> list[Path]:
    """遞迴列出指定副檔名的檔案。

    會忽略常見的無關資料夾，例如 `.git`、`node_modules` 等。"""
    # 忽略的資料夾名稱
    #
    # - agent_runtime：mcp 會在此建立 sandbox 工作區，裡面包含複製的 repo，搜尋程式碼時不應納入
    # - sandbox_workspaces／sandbox_worktrees：隔離修改環境，屬於 agent_runtime 內的子目錄
    IGNORE_DIRS = {
        ".venv",
        "venv",
        "__pycache__",
        ".git",
        "node_modules",
        "dist",
        "build",
        "agent_runtime",
        "sandbox_workspaces",
        "sandbox_worktrees",
    }
    results: list[Path] = []
    for file in root.rglob("*"):
        # 若路徑包含要忽略的資料夾則跳過
        if any(part in IGNORE_DIRS for part in file.parts):
            continue
        if file.is_file() and file.suffix in extensions:
            results.append(file)
    return results