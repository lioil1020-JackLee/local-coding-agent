from __future__ import annotations

"""
settings 模組

提供整個系統的路徑配置。當啟動 MCP server 或工具時，可以透過
``Settings.load()`` 取得工作目錄（workspace）、執行期目錄（runtime）、
sessions 及其他子目錄的路徑。這裡的實作仿照遠端版本，使用環境
變數 ``REPO_GUARDIAN_WORKSPACE_ROOT`` 指定專案根目錄，若未指定則
預設為當前工作目錄 ``."。``

所有路徑皆會轉為 ``Path`` 物件並解析絕對路徑。這讓呼叫方無須自行
拼接路徑即可在本地檔案系統存取資源。
"""

import os
from pathlib import Path
from pydantic import BaseModel


class Settings(BaseModel):
    """系統設定。包含各種目錄路徑。"""

    workspace_root: Path
    runtime_root: Path
    sessions_root: Path
    logs_root: Path
    snapshots_root: Path
    sandbox_root: Path

    @classmethod
    def load(cls) -> "Settings":
        """
        根據環境變數載入設定。

        回傳一個 ``Settings`` 實例，其中所有路徑都已解析為絕對路徑。
        如果環境變數 ``REPO_GUARDIAN_WORKSPACE_ROOT`` 未設定，預設使用
        當前目錄 (``."``)。
        """
        workspace_root = Path(
            os.environ.get("REPO_GUARDIAN_WORKSPACE_ROOT", ".")
        ).resolve()

        runtime_root = workspace_root / "agent_runtime"

        return cls(
            workspace_root=workspace_root,
            runtime_root=runtime_root,
            sessions_root=runtime_root / "sessions",
            logs_root=runtime_root / "logs",
            snapshots_root=runtime_root / "snapshots",
            sandbox_root=runtime_root / "sandbox_worktrees",
        )