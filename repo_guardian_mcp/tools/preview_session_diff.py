from __future__ import annotations

import difflib
from pathlib import Path
from typing import Any

from repo_guardian_mcp.services.session_service import SessionService

_IGNORED_PATH_PARTS = {
    "agent_runtime",
    ".venv",
    "venv",
    "__pycache__",
    ".pytest_cache",
    ".mypy_cache",
    ".ruff_cache",
    ".git",
}
_IGNORED_SUFFIXES = {".pyc", ".pyo", ".pyd", ".so", ".dll"}


def _read_text_or_empty(path: Path) -> str:
    if not path.exists() or not path.is_file():
        return ""
    try:
        return path.read_text(encoding="utf-8")
    except UnicodeDecodeError:
        return path.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return ""


def _find_sessions_dir(start: Path, session_id: str) -> Path:
    current = start.resolve()
    while True:
        candidate = current / "agent_runtime" / "sessions"
        if (candidate / f"{session_id}.json").exists():
            return candidate
        if current.parent == current:
            break
        current = current.parent
    return (start.resolve() / "agent_runtime" / "sessions").resolve()


def _should_ignore(relative_path: Path) -> bool:
    if any(part in _IGNORED_PATH_PARTS for part in relative_path.parts):
        return True
    if relative_path.suffix.lower() in _IGNORED_SUFFIXES:
        return True
    return False


def preview_session_diff(session_id: str) -> dict[str, Any]:
    sessions_dir = _find_sessions_dir(Path.cwd(), session_id)
    session_service = SessionService(str(sessions_dir))
    session = session_service.load_session(session_id)

    repo_root = Path(session.repo_root).resolve()
    sandbox_root = Path(session.sandbox_path).resolve()

    if not sandbox_root.exists():
        return {
            "ok": False,
            "session_id": session_id,
            "error": f"sandbox 不存在: {sandbox_root}",
        }

    changed_files: list[str] = []
    diff_blocks: list[str] = []

    for sandbox_file in sandbox_root.rglob("*"):
        if not sandbox_file.is_file():
            continue

        relative_path = sandbox_file.relative_to(sandbox_root)
        if _should_ignore(relative_path):
            continue

        repo_file = repo_root / relative_path
        repo_text = _read_text_or_empty(repo_file)
        sandbox_text = _read_text_or_empty(sandbox_file)

        if repo_text == sandbox_text:
            continue

        normalized_relative = str(relative_path).replace("\\", "/")
        changed_files.append(normalized_relative)

        unified = "".join(
            difflib.unified_diff(
                repo_text.splitlines(keepends=True),
                sandbox_text.splitlines(keepends=True),
                fromfile=normalized_relative,
                tofile=normalized_relative,
            )
        ).strip()

        if unified:
            diff_blocks.append(unified)

    diff_text = "\n\n".join(diff_blocks)

    return {
        "ok": True,
        "session_id": session_id,
        "base_commit": session.base_commit,
        "changed_files": changed_files,
        "diff": diff_text,
        "diff_text": diff_text,
    }
