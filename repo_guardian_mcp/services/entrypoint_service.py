from __future__ import annotations

"""
entrypoint_service

提供專案入口點的搜尋功能。這個服務會呼叫 ``RepoScanService`` 的
``find_entrypoints`` 方法，並沿用它的忽略規則，避免將 sandbox worktree
或其他執行期資料夾視為真正的專案檔案。

使用者可以透過此服務取得較像入口的 Python 檔案清單，例如 ``main.py``、
``app.py`` 等，以便快速瞭解專案的啟動方式。
"""

from repo_guardian_mcp.services.repo_scan_service import RepoScanService


def get_entrypoints(repo_root: str, limit: int = 12) -> list[str]:
    """
    回傳目前 repo 中較像入口點的 Python 檔案清單。

    參數：
        repo_root (str): 專案根目錄。
        limit (int): 限制回傳的檔案數量，預設 12。

    回傳：
        list[str]: 找到的入口檔案相對路徑。
    """
    service = RepoScanService()
    return service.find_entrypoints(repo_root=repo_root, limit=limit)