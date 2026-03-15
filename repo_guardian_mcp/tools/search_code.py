from __future__ import annotations

from pathlib import Path

from repo_guardian_mcp.services.symbol_service import SymbolService


def search_code(
    workspace_root: Path,
    query: str,
) -> list[dict]:
    """在專案中搜尋程式碼關鍵字。"""
    service = SymbolService(workspace_root)
    return service.search(query)