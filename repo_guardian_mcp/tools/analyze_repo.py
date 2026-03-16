from __future__ import annotations

from pathlib import Path

from repo_guardian_mcp.services.repo_scan_service import RepoScanService


def analyze_repo_tool(repo_root: str) -> dict:
    """提供給 Continue / MCP 的專案總覽工具。

    重點：
    - 只做唯讀分析
    - 排除 agent_runtime/sandbox_worktrees 等執行期資料夾
    - 給出新手看得懂的摘要欄位
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


# 保留常見別名，讓既有 MCP 註冊或其他模組匯入時不用一起改。
analyze_repo = analyze_repo_tool
