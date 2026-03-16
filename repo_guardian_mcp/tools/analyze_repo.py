from __future__ import annotations

from typing import Any

from repo_guardian_mcp.tools.repo_overview import repo_overview
from repo_guardian_mcp.tools.find_entrypoints import find_entrypoints
from repo_guardian_mcp.tools.symbol_index import symbol_index


def analyze_repo(repo_root: str) -> dict[str, Any]:
    """
    高階 repo 分析工具
    """

    overview = repo_overview(repo_root)

    entrypoints = find_entrypoints(repo_root)

    symbols = symbol_index(repo_root)

    return {
        "ok": True,
        "repo": overview,
        "entrypoints": entrypoints,
        "symbol_count": len(symbols),
        "suggested_next_files": [
            "repo_guardian_mcp/server.py",
            "repo_guardian_mcp/tools/",
            "repo_guardian_mcp/services/",
        ],
    }