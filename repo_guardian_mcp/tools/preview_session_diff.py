from __future__ import annotations

"""
preview_session_diff 工具

此工具比較 repo_root 與 sandbox 工作區的檔案內容，產生 unified diff。它在 copy-based
sandbox 模式下不再依賴 git，直接逐檔比較差異。為了讓 replace 模式的細微差
異也能顯示，額外提供字串級別的 diff 段落，以便驗證測試能確認替換的字串。
"""

import difflib
from pathlib import Path
from typing import Dict, List

from repo_guardian_mcp.services.session_service import SessionService


def _read_text_or_empty(path: Path) -> str:
    if not path.exists() or not path.is_file():
        return ""
    return path.read_text(encoding="utf-8")


def _build_fragment_diff(before: str, after: str) -> str:
    """
    建立更細的 replace 片段 diff。

    unified_diff 以整行為單位，無法反映細粒度的字串差異。為了在測試中確認被替換
    的舊字串與新字串出現在 diff 中，這裡利用 difflib.SequenceMatcher 額外補上一層
    字串級別差異。
    """
    blocks: List[str] = []
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


def preview_session_diff(session_id: str) -> Dict[str, any]:
    """
    預覽指定 session 的差異。

    此函式會嘗試在當前工作目錄及其祖先目錄尋找 ``agent_runtime/sessions``
    資料夾，以載入 session 資訊。成功載入後會比較 repo_root 與 sandbox 內的檔案內容，
    產生 unified diff 與字串差異摘要。若 sandbox 不存在，則回傳錯誤訊息。
    """
    # 嘗試向上尋找 session 檔案所在的資料夾
    cwd = Path.cwd().resolve()
    session_file_path = None
    candidate = cwd
    while True:
        sessions_dir = candidate / "agent_runtime" / "sessions"
        file_path = sessions_dir / f"{session_id}.json"
        if file_path.exists():
            session_file_path = file_path
            break
        if candidate.parent == candidate:
            # 已達檔案系統根目錄
            break
        candidate = candidate.parent

    if session_file_path is None:
        # 如果找不到 session 檔案，仍嘗試使用當前目錄的 sessions_dir 以提供較友善的錯誤訊息
        sessions_dir = cwd / "agent_runtime" / "sessions"
    else:
        sessions_dir = session_file_path.parent

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

    changed_files: List[str] = []
    diff_blocks: List[str] = []

    for path in sandbox_root.rglob("*"):
        if not path.is_file():
            continue

        relative_path = path.relative_to(sandbox_root)

        # 排除 agent_runtime 內的檔案
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