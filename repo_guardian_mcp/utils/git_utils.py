from __future__ import annotations

import json
import shutil
import subprocess
import time
from datetime import datetime
from pathlib import Path

GIT_TIMEOUT_SECONDS = 120


def _write_git_debug_log(repo_path: Path, payload: dict) -> None:
    try:
        log_path = repo_path / "agent_runtime" / "git_debug.log"
        log_path.parent.mkdir(parents=True, exist_ok=True)
        with log_path.open("a", encoding="utf-8") as f:
            f.write(json.dumps(payload, ensure_ascii=False) + "\n")
    except Exception:
        # debug log 失敗不能影響主流程
        pass


def run_git_command(repo_path: Path, args: list[str]) -> str:
    """在指定 repo 路徑執行 git 指令"""
    start = time.time()

    _write_git_debug_log(
        repo_path,
        {
            "ts": datetime.now().isoformat(),
            "event": "git_command:start",
            "args": args,
        },
    )

    try:
        result = subprocess.run(
            ["git"] + args,
            cwd=repo_path,
            capture_output=True,
            text=True,
            timeout=GIT_TIMEOUT_SECONDS,
        )
    except subprocess.TimeoutExpired as exc:
        duration = round(time.time() - start, 3)
        _write_git_debug_log(
            repo_path,
            {
                "ts": datetime.now().isoformat(),
                "event": "git_command:timeout",
                "args": args,
                "seconds": duration,
            },
        )
        raise RuntimeError(f"git 指令逾時: {' '.join(args)}") from exc

    duration = round(time.time() - start, 3)

    _write_git_debug_log(
        repo_path,
        {
            "ts": datetime.now().isoformat(),
            "event": "git_command:end",
            "args": args,
            "seconds": duration,
            "returncode": result.returncode,
        },
    )

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

    start = time.time()
    _write_git_debug_log(
        repo_path,
        {
            "ts": datetime.now().isoformat(),
            "event": "git_worktree:start",
            "branch_name": branch_name,
            "sandbox_path": str(sandbox_path),
            "base_commit": base_commit,
        },
    )

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
        duration = round(time.time() - start, 3)
        _write_git_debug_log(
            repo_path,
            {
                "ts": datetime.now().isoformat(),
                "event": "git_worktree:timeout",
                "branch_name": branch_name,
                "seconds": duration,
            },
        )
        raise RuntimeError(f"git worktree 建立逾時: {branch_name}") from exc

    duration = round(time.time() - start, 3)

    _write_git_debug_log(
        repo_path,
        {
            "ts": datetime.now().isoformat(),
            "event": "git_worktree:end",
            "branch_name": branch_name,
            "seconds": duration,
            "returncode": result.returncode,
        },
    )

    if result.returncode != 0:
        raise RuntimeError(f"git worktree 建立失敗: {branch_name}\n{result.stderr}")


def get_diff_against_commit(repo_path: Path, base_commit: str) -> str:
    return run_git_command(repo_path, ["diff", base_commit])