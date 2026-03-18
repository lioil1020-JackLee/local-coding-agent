from __future__ import annotations

"""
analyze_repo 工具

此工具提供專案總覽，用於幫助使用者快速了解專案結構和重點檔案。它僅進行
唯讀分析，依賴 ``RepoScanService`` 掃描專案，並返回容易理解的摘要資訊。
"""

from pathlib import Path

from repo_guardian_mcp.services.repo_scan_service import RepoScanService


def analyze_repo_tool(repo_root: str) -> dict:
    """
    提供專案總覽工具，給予資料整理後的摘要。

    參數：
        repo_root (str): 專案根目錄。

    回傳：
        dict: 包含 ``ok``、``project_name``、``top_level_directories`` 等資料的字典。
    """
    root = Path(repo_root).resolve()
    service = RepoScanService()
    summary = service.summarize_repo(root)

    focus_files: list[str] = []
    for rel in summary.important_files + summary.entrypoints:
        if rel not in focus_files:
            focus_files.append(rel)

    return {
        "ok": True,
        "repo_root": str(root),
        "project_name": root.name,
        "top_level_directories": summary.top_level_directories,
        "total_files": summary.total_files,
        "total_python_files": summary.total_python_files,
        "important_files": summary.important_files,
        "entrypoints": summary.entrypoints,
        "focus_files": focus_files[:12],
        "summary": {
            "project_name": root.name,
            "start_here": focus_files[:5],
            "notes": [
                "分析時已排除 agent_runtime、.venv、__pycache__ 等執行期或快取資料夾。",
                "entrypoints 只列出真正 repo 內較像入口的 Python 檔案，不包含 sandbox worktree 複本。",
            ],
        },
    }


# 保留別名，讓既有程式或 MCP 註冊引用不需一起改名
analyze_repo = analyze_repo_tool