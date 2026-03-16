
from __future__ import annotations

import subprocess
import shutil
from pathlib import Path

GIT_TIMEOUT_SECONDS = 30


def run_git_command(repo_path: Path, args: list[str]) -> str:
    """在指定 repo 路徑執行 git 指令"""

    try:
        result = subprocess.run(
            ["git"] + args,
            cwd=repo_path,
            capture_output=True,
            text=True,
            timeout=GIT_TIMEOUT_SECONDS,
        )
    except subprocess.TimeoutExpired as exc:
        raise RuntimeError(f"git 指令逾時: {' '.join(args)}") from exc

    if result.returncode != 0:
        raise RuntimeError(f"git 指令失敗: {' '.join(args)}\n{result.stderr}")

    return result.stdout.strip()


def get_current_branch(repo_path: Path) -> str:
    return run_git_command(repo_path, ["rev-parse", "--abbrev-ref", "HEAD"])


def get_git_status(repo_path: Path) -> str:
    return run_git_command(repo_path, ["status", "--short"])


def get_last_commit(repo_path: Path) -> str:
    return run_git_command(repo_path, ["log", "-1", "--oneline"])


def get_head_commit(repo_path: Path) -> str:
    return run_git_command(repo_path, ["rev-parse", "HEAD"])


def create_git_worktree(repo_path: Path, sandbox_path: Path, branch_name: str, base_commit: str) -> None:
    """建立新的 git worktree (加入防呆避免卡住)"""

    sandbox_path = sandbox_path.resolve()

    if sandbox_path.exists():
        try:
            shutil.rmtree(sandbox_path)
        except Exception:
            pass

    sandbox_path.parent.mkdir(parents=True, exist_ok=True)

    try:
        result = subprocess.run(
            [
                "git",
                "worktree",
                "add",
                "-f",
                "-b",
                branch_name,
                str(sandbox_path),
                base_commit,
            ],
            cwd=repo_path,
            capture_output=True,
            text=True,
            timeout=GIT_TIMEOUT_SECONDS,
        )
    except subprocess.TimeoutExpired as exc:
        raise RuntimeError(f"git worktree 建立逾時: {branch_name}") from exc

    if result.returncode != 0:
        raise RuntimeError(f"git worktree 建立失敗: {branch_name}\n{result.stderr}")


def get_diff_against_commit(repo_path: Path, base_commit: str) -> str:
    return run_git_command(repo_path, ["diff", base_commit])
