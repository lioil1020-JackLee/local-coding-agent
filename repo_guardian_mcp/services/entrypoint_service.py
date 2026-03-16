from __future__ import annotations

from repo_guardian_mcp.services.repo_scan_service import RepoScanService


def get_entrypoints(repo_root: str, limit: int = 12) -> list[str]:
    """回傳目前 repo 中較像入口點的 Python 檔案。

    這裡直接委派給 RepoScanService，並沿用它的忽略規則，
    避免把 sandbox worktree 裡的複本誤判成真正入口點。
    """
    service = RepoScanService()
    return service.find_entrypoints(repo_root=repo_root, limit=limit)
