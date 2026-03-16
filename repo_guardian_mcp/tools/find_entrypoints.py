from __future__ import annotations

from repo_guardian_mcp.services.entrypoint_service import get_entrypoints


def find_entrypoints(repo_root: str, limit: int = 12) -> dict:
    """列出專案入口點候選。"""
    entrypoints = get_entrypoints(repo_root=repo_root, limit=limit)
    return {
        "ok": True,
        "repo_root": repo_root,
        "entrypoints": entrypoints,
        "count": len(entrypoints),
    }


# 保留舊名稱，避免 Continue / 其他呼叫端因函式名稱不同而失效。
get_entrypoints_tool = find_entrypoints
