from __future__ import annotations

import shutil
from pathlib import Path


DEFAULT_IGNORED_DIRS = {
    ".git",
    ".venv",
    "__pycache__",
    ".pytest_cache",
    ".mypy_cache",
    "node_modules",
    "agent_runtime",
}

DEFAULT_IGNORED_FILES = {
    ".DS_Store",
}


def _should_skip_path(path: Path, repo_root: Path) -> bool:
    """
    判斷這個路徑是否應該跳過複製。

    這一版故意用白名單思維中的「排除大且不必要內容」：
    - 不複製 .git
    - 不複製 agent_runtime
    - 不複製虛擬環境與快取
    """
    try:
        relative_parts = path.relative_to(repo_root).parts
    except ValueError:
        return True

    if not relative_parts:
        return False

    top = relative_parts[0]

    if top in DEFAULT_IGNORED_DIRS:
        return True

    if path.name in DEFAULT_IGNORED_FILES:
        return True

    return False


def prepare_copy_sandbox(
    repo_root: str | Path,
    sandbox_path: str | Path,
) -> str:
    """
    建立 copy-based sandbox。

    設計目標：
    - 不用 git worktree
    - 避免 Continue MCP 在 create session 時卡住 timeout
    - 保留專案主要檔案，讓後續 edit / diff / validation 可運作
    """
    repo_root_path = Path(repo_root).resolve()
    sandbox_root = Path(sandbox_path).resolve()

    if not repo_root_path.exists():
        raise FileNotFoundError(f"repo_root 不存在: {repo_root_path}")

    if sandbox_root.exists():
        shutil.rmtree(sandbox_root)

    sandbox_root.mkdir(parents=True, exist_ok=True)

    for item in repo_root_path.iterdir():
        if _should_skip_path(item, repo_root_path):
            continue

        target = sandbox_root / item.name

        if item.is_dir():
            shutil.copytree(
                item,
                target,
                dirs_exist_ok=True,
                ignore=shutil.ignore_patterns(
                    "__pycache__",
                    ".pytest_cache",
                    ".mypy_cache",
                    ".venv",
                    "node_modules",
                    "agent_runtime",
                    ".git",
                ),
            )
        else:
            shutil.copy2(item, target)

    return str(sandbox_root)


def cleanup_copy_sandbox(sandbox_path: str | Path) -> None:
    """
    清理 copy-based sandbox。
    """
    sandbox_root = Path(sandbox_path).resolve()
    if sandbox_root.exists():
        shutil.rmtree(sandbox_root)
