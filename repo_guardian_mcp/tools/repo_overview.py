from __future__ import annotations

from pathlib import Path
from typing import Any

from repo_guardian_mcp.services.repo_scan_service import RepoScanService



def _build_overview(repo_root: str | None = None) -> dict[str, Any]:
    """建立穩定的 repo 總覽結果。

    這裡保留舊測試會用到的欄位，
    同時也讓新版本的分析工具可以共用同一份資料。
    """
    root = Path(repo_root).resolve() if repo_root else Path.cwd().resolve()
    service = RepoScanService()
    summary = service.summarize_repo(root)

    return {
        "project_name": root.name,
        "repo_root": str(root),
        "top_level_directories": summary.top_level_directories,
        "important_files": summary.important_files,
        "entrypoints": summary.entrypoints,
        "file_count": summary.total_files,
        "python_file_count": summary.total_python_files,
        "summary": "repo overview generated",
    }



def repo_overview_tool(repo_root: str | None = None) -> dict[str, Any]:
    """新版工具入口。"""
    overview = _build_overview(repo_root=repo_root)
    return {
        "ok": True,
        "tool": "repo_overview",
        "repo_root": overview["repo_root"],
        "summary": overview["summary"],
        "data": overview,
    }



def repo_overview(repo_root: str | None = None) -> dict[str, Any]:
    """舊版函式名稱相容層。"""
    overview = _build_overview(repo_root=repo_root)
    return {
        "ok": True,
        **overview,
    }


get_repo_overview = repo_overview



def run(repo_root: str | None = None) -> dict[str, Any]:
    """提供 pytest 與舊呼叫方式相容。"""
    return repo_overview(repo_root=repo_root)
