from __future__ import annotations

"""
sandbox_service 提供建立與清理 copy-based sandbox 的功能。

使用 copytree 而非 git worktree，以減少 git 相關限制並提升速度。
"""

import os
import shutil
import stat
import time
from pathlib import Path
from typing import Callable


_IGNORE_NAMES = {
    ".git",
    ".hg",
    ".svn",
    ".idea",
    ".vscode",
    ".mypy_cache",
    ".pytest_cache",
    ".ruff_cache",
    "__pycache__",
    ".tmp_pytest",
    ".pytest_tmp",
    "pytest_tmp",
    ".tmp.driveupload",
    ".tmp",
    "..tmppytest",
    "tmp_pytest_local",
}

_IGNORE_NAME_PREFIXES = (
    ".tmp-",
    "..tmp",
    ".tmp_pytest",
    ".pytest_tmp",
    "pytest-of-",
    "pytest-",
    "pytest_tmp",
    "tmp_pytest",
)

_IGNORE_DIR_PREFIXES = (
    "agent_runtime/sandbox_workspaces",
    "agent_runtime/sandbox_worktrees",
    "agent_runtime/pytest",
)

IgnoreFn = Callable[[str, list[str]], set[str]]


def _to_path(value: str | Path) -> Path:
    return value if isinstance(value, Path) else Path(value)


def get_runtime_root(repo_root: str | Path) -> Path:
    return _to_path(repo_root) / "agent_runtime"


def get_sandbox_workspaces_root(repo_root: str | Path) -> Path:
    root = get_runtime_root(repo_root) / "sandbox_workspaces"
    root.mkdir(parents=True, exist_ok=True)
    return root


def get_sandbox_path(repo_root: str | Path, session_id: str) -> Path:
    return get_sandbox_workspaces_root(repo_root) / session_id


def _default_ignore(repo_root: Path) -> IgnoreFn:
    repo_root = repo_root.resolve()

    def ignore(directory: str, names: list[str]) -> set[str]:
        directory_path = Path(directory)
        ignored = {
            name
            for name in names
            if name in _IGNORE_NAMES or any(name.startswith(prefix) for prefix in _IGNORE_NAME_PREFIXES)
        }
        for name in names:
            if name in ignored:
                continue
            try:
                candidate = (directory_path / name).resolve()
            except OSError:
                ignored.add(name)
                continue
            try:
                if candidate.is_dir():
                    if not os.access(candidate, os.R_OK | os.X_OK):
                        ignored.add(name)
                        continue
                elif candidate.exists() and not os.access(candidate, os.R_OK):
                    ignored.add(name)
                    continue
            except OSError:
                ignored.add(name)
                continue
            try:
                rel = candidate.relative_to(repo_root)
            except ValueError:
                continue
            rel_posix = rel.as_posix()
            if any(
                rel_posix == prefix or rel_posix.startswith(prefix + "/")
                for prefix in _IGNORE_DIR_PREFIXES
            ):
                ignored.add(name)
        return ignored

    return ignore


def _resolve_target_sandbox_path(
    *,
    repo_root: str | Path,
    session_id: str | None = None,
    sandbox_path: str | Path | None = None,
) -> Path:
    if sandbox_path is not None:
        return _to_path(sandbox_path).resolve()
    if not session_id:
        raise ValueError("session_id 或 sandbox_path 至少要提供一個")
    return get_sandbox_path(repo_root, session_id).resolve()


# Backward and forward compatible.
# Some callers only pass (repo_root, session_id), while newer callers also pass
# sandbox_path as a keyword. Keep both forms working.
def create_copy_sandbox(
    repo_root: str | Path,
    session_id: str | None = None,
    *,
    sandbox_path: str | Path | None = None,
    ignore: IgnoreFn | None = None,
    **_: object,
) -> Path:
    repo_root_path = _to_path(repo_root).resolve()
    target_sandbox = _resolve_target_sandbox_path(
        repo_root=repo_root_path,
        session_id=session_id,
        sandbox_path=sandbox_path,
    )

    if target_sandbox.exists():
        shutil.rmtree(target_sandbox, ignore_errors=True)
    target_sandbox.parent.mkdir(parents=True, exist_ok=True)
    shutil.copytree(
        repo_root_path,
        target_sandbox,
        ignore=ignore or _default_ignore(repo_root_path),
        dirs_exist_ok=False,
    )
    return target_sandbox


def prepare_copy_sandbox(
    repo_root: str | Path,
    session_id: str | None = None,
    *,
    sandbox_path: str | Path | None = None,
    ignore: IgnoreFn | None = None,
    **kwargs: object,
) -> str:
    sandbox_root = create_copy_sandbox(
        repo_root=repo_root,
        session_id=session_id,
        sandbox_path=sandbox_path,
        ignore=ignore,
        **kwargs,
    )
    return str(sandbox_root)


def _handle_remove_readonly(func, path, exc_info) -> None:
    try:
        os.chmod(path, stat.S_IWRITE)
        func(path)
    except Exception:
        pass


def cleanup_copy_sandbox(
    sandbox_root: str | Path,
    retries: int = 5,
    delay_seconds: float = 0.2,
) -> None:
    sandbox_path = _to_path(sandbox_root)
    if not sandbox_path.exists():
        return

    last_error: Exception | None = None
    for attempt in range(retries):
        try:
            shutil.rmtree(sandbox_path, onerror=_handle_remove_readonly)
            return
        except PermissionError as exc:
            last_error = exc
            time.sleep(delay_seconds * (attempt + 1))
        except FileNotFoundError:
            return

    if sandbox_path.exists() and last_error is not None:
        raise last_error


__all__ = [
    "cleanup_copy_sandbox",
    "create_copy_sandbox",
    "get_runtime_root",
    "get_sandbox_path",
    "get_sandbox_workspaces_root",
    "prepare_copy_sandbox",
]
