from __future__ import annotations

"""
repo_overview 工具

產生專案概覽，包括專案名稱、根目錄、頂層目錄、重點檔案、
入口點、檔案數量等。此工具使用 RepoScanService 來取得資訊。

提供兩個介面：
 - repo_overview_tool: 回傳帶有標記的結果，適合工具呼叫。
 - repo_overview: 舊版函式名稱，相容舊呼叫方式。
"""

from pathlib import Path
from typing import Any

from repo_guardian_mcp.services.repo_scan_service import RepoScanService


def _build_overview(repo_root: str | None = None) -> dict[str, Any]:
    """建立穩定的 repo 總覽資料。"""
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
    """新版工具入口，回傳帶有工具名稱的結果。"""
    overview = _build_overview(repo_root=repo_root)
    return {
        "ok": True,
        "tool": "repo_overview",
        "repo_root": overview["repo_root"],
        "summary": overview["summary"],
        "data": overview,
    }


def repo_overview(repo_root: str | None = None) -> dict[str, Any]:
    """舊版函式名稱，直接回傳總覽資料。"""
    overview = _build_overview(repo_root=repo_root)
    return {
        "ok": True,
        **overview,
    }


get_repo_overview = repo_overview


def run(repo_root: str | None = None) -> dict[str, Any]:
    """pytest 與舊呼叫方式相容的入口。"""
    return repo_overview(repo_root=repo_root)