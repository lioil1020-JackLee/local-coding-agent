from __future__ import annotations

import subprocess
from pathlib import Path


def run_git_command(repo_path: Path, args: list[str]) -> str:
    """
    在指定 repo 路徑執行 git 指令。
    """

    result = subprocess.run(
        ["git"] + args,
        cwd=repo_path,
        capture_output=True,
        text=True,
    )

    if result.returncode != 0:
        raise RuntimeError(
            f"git 指令失敗: {' '.join(args)}\n{result.stderr}"
        )

    return result.stdout.strip()


def get_current_branch(repo_path: Path) -> str:
    """
    取得目前 git branch。
    """

    return run_git_command(repo_path, ["rev-parse", "--abbrev-ref", "HEAD"])


def get_git_status(repo_path: Path) -> str:
    """
    取得 git status。
    """

    return run_git_command(repo_path, ["status", "--short"])


def get_last_commit(repo_path: Path) -> str:
    """
    取得最後一個 commit (含 commit message)。
    """

    return run_git_command(repo_path, ["log", "-1", "--oneline"])


def get_head_commit(repo_path: Path) -> str:
    """
    取得目前 HEAD commit SHA。
    只回傳純 SHA，不包含 commit message。
    """

    return run_git_command(repo_path, ["rev-parse", "HEAD"])