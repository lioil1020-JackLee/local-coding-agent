from __future__ import annotations

"""
find_entrypoints 工具

這個工具調用 ``entrypoint_service.get_entrypoints`` 來列出專案可能的入口點，
並包裝成符合 MCP contract 的回傳格式。主要用於 Continue 或其他呼叫端在分析
階段取得候選入口檔案。
"""

from repo_guardian_mcp.services.entrypoint_service import get_entrypoints


def find_entrypoints(repo_root: str, limit: int = 12) -> dict:
    """
    列出專案入口點候選。

    參數：
        repo_root (str): 專案根目錄。
        limit (int): 限制回傳的候選數量，預設 12。

    回傳：
        dict: 包含 ``ok``、``entrypoints`` 與相關資訊的字典。
    """
    entrypoints = get_entrypoints(repo_root=repo_root, limit=limit)
    return {
        "ok": True,
        "repo_root": repo_root,
        "entrypoints": entrypoints,
        "count": len(entrypoints),
    }


# 舊名稱別名，避免 Continue 或其他呼叫端因函式名稱不同而失效。
get_entrypoints_tool = find_entrypoints