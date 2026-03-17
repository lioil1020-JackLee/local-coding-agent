from __future__ import annotations

import difflib
from pathlib import Path

from repo_guardian_mcp.services.session_service import SessionService


def _read_text_or_empty(path: Path) -> str:
    if not path.exists() or not path.is_file():
        return ""
    return path.read_text(encoding="utf-8")


def _build_fragment_diff(before: str, after: str) -> str:
    """
    建立更細的 replace 片段 diff。

    為什麼需要這層：
    - unified_diff 以「整行」為主
    - 但目前測試會檢查被替換的舊字串 / 新字串是否直接出現在 diff 內
    - 所以這裡補一層較細的字串級差異，讓 replace 情境更穩定
    """
    blocks: list[str] = []
    matcher = difflib.SequenceMatcher(a=before, b=after)

    for tag, i1, i2, j1, j2 in matcher.get_opcodes():
        if tag == "equal":
            continue

        old_chunk = before[i1:i2]
        new_chunk = after[j1:j2]

        if old_chunk:
            for line in old_chunk.splitlines():
                if line:
                    blocks.append(f"-{line}")

        if new_chunk:
            for line in new_chunk.splitlines():
                if line:
                    blocks.append(f"+{line}")

    return "\n".join(blocks)


def preview_session_diff(session_id: str) -> dict:
    """
    預覽 session 的差異。

    方案 B 不再依賴 git diff，
    改成直接比較 repo_root 與 sandbox 中的檔案內容。
    """
    repo_root_guess = Path.cwd().resolve()
    sessions_dir = repo_root_guess / "agent_runtime" / "sessions"

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

    for path in sandbox_root.rglob("*"):
        if not path.is_file():
            continue

        relative_path = path.relative_to(sandbox_root)

        if "agent_runtime" in relative_path.parts:
            continue

        repo_file = repo_root / relative_path
        sandbox_file = sandbox_root / relative_path

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
        )

        fragment = _build_fragment_diff(repo_text, sandbox_text)

        block_parts = [unified.strip()]
        if fragment.strip():
            block_parts.append(fragment.strip())

        diff_blocks.append("\n".join(part for part in block_parts if part))

    diff_text = "\n\n".join(diff_blocks)

    return {
        "ok": True,
        "session_id": session_id,
        "base_commit": session.base_commit,
        "changed_files": changed_files,
        "diff": diff_text,
        "diff_text": diff_text,
    }
