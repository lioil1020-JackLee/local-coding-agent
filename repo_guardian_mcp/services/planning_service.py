from __future__ import annotations

from pathlib import Path

from repo_guardian_mcp.services.symbol_service import SymbolService


class PlanningService:
    """負責做簡單的影響分析與修改規劃。"""

    def __init__(self, workspace_root: Path):
        self.workspace_root = workspace_root
        self.symbol_service = SymbolService(workspace_root)

    def impact_analysis(self, symbol_name: str) -> dict:
        """分析指定 symbol 在 repo 中可能的影響範圍。"""
        symbol_hits = []
        reference_hits = []

        symbol_index = self.symbol_service.build_symbol_index()
        search_results = self.symbol_service.search(symbol_name)

        for item in symbol_index:
            if item["name"] == symbol_name:
                symbol_hits.append(item)

        for item in search_results:
            reference_hits.append(item)

        return {
            "symbol_name": symbol_name,
            "defined_symbols": symbol_hits,
            "references": reference_hits,
            "summary": (
                f"找到 {len(symbol_hits)} 個定義位置，"
                f"{len(reference_hits)} 個可能引用位置。"
            ),
        }