from __future__ import annotations

"""
move_file 工具

在 sandbox 中移動或重新命名檔案。此工具主要用於高階重構任務，例如
將檔案移動到其他資料夾或重新命名檔案。它只會對指定 session
的 sandbox 發生作用，不會直接修改主 repo。

輸入參數：
    session_id (str): 要操作的 session ID。
    src (str): 要移動的檔案相對路徑，相對於 repo 根目錄。
    dest (str): 目標檔案相對路徑，相對於 repo 根目錄。

回傳：
    dict: 包含 ``ok``、``moved``、``from``、``to`` 或 ``error``。若移動失敗，``ok`` 為 False，並包含錯誤訊息。
"""

import os
import shutil
from typing import Any, Dict

from repo_guardian_mcp.services import session_service


def move_file(session_id: str, src: str, dest: str) -> Dict[str, Any]:
    """在指定 session 的 sandbox 中移動檔案。"""
    if not session_id:
        return {
            "ok": False,
            "error": "session_id is required",
        }
    if not src or not dest:
        return {
            "ok": False,
            "error": "src and dest are required",
        }
    try:
        session = session_service.load_session(session_id)
    except Exception as exc:
        return {
            "ok": False,
            "error": f"Failed to load session: {exc}",
        }
    sandbox_path = session.get("sandbox_path")
    if not sandbox_path:
        return {
            "ok": False,
            "error": "sandbox_path not found in session",
        }
    # 組合絕對路徑
    src_path = os.path.join(sandbox_path, src)
    dest_path = os.path.join(sandbox_path, dest)
    if not os.path.exists(src_path):
        return {
            "ok": False,
            "error": f"source file not found: {src}",
        }
    # 確保目標資料夾存在
    dest_dir = os.path.dirname(dest_path)
    os.makedirs(dest_dir, exist_ok=True)
    try:
        shutil.move(src_path, dest_path)
    except Exception as exc:
        return {
            "ok": False,
            "error": f"Failed to move file: {exc}",
        }
    return {
        "ok": True,
        "moved": True,
        "from": src,
        "to": dest,
    }