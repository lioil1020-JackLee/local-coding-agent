from __future__ import annotations

import json
from pathlib import Path
from typing import Any


def update_session_file(
    repo_root: str,
    session_id: str,
    updates: dict[str, Any],
) -> str:
    """
    更新 agent_runtime/sessions/<session_id>.json
    回傳 session 檔案路徑。
    """

    if not repo_root or not repo_root.strip():
        raise ValueError("repo_root 不能為空")

    if not session_id or not session_id.strip():
        raise ValueError("session_id 不能為空")

    session_file = Path(repo_root) / "agent_runtime" / "sessions" / f"{session_id}.json"

    if not session_file.exists():
        raise ValueError(f"找不到 session 檔案: {session_file}")

    data = json.loads(session_file.read_text(encoding="utf-8"))

    if not isinstance(data, dict):
        raise ValueError("session 檔案內容不是 dict")

    data.update(updates)

    session_file.write_text(
        json.dumps(data, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    return str(session_file)