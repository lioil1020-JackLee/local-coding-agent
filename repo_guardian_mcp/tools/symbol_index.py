from __future__ import annotations

from pathlib import Path

from repo_guardian_mcp.services.symbol_service import SymbolService


def symbol_index(workspace_root: Path) -> list[dict]:
    """建立目前 repo 的 Python symbol 索引。"""
    service = SymbolService(workspace_root)
    return service.build_symbol_index()