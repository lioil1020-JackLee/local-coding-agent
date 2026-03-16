
from __future__ import annotations

from pathlib import Path
from typing import Dict, List

from repo_guardian_mcp.services.symbol_service import SymbolService


class PlanningService:
    """
    負責做影響分析與後續修改規劃。
    Phase 2: 強化 impact analysis 結果結構。
    """

    def __init__(self, workspace_root: Path):
        self.workspace_root = workspace_root
        self.symbol_service = SymbolService(workspace_root)

    def impact_analysis(self, symbol_name: str) -> Dict:
        """
        分析指定 symbol 在 repo 中的影響範圍。
        回傳結構化結果，讓 orchestrator 能使用。
        """

        symbol_hits: List[dict] = []
        reference_hits: List[dict] = []
        affected_files: set[str] = set()

        # 建立 symbol index
        symbol_index = self.symbol_service.build_symbol_index()

        # 搜尋 symbol references
        search_results = self.symbol_service.search(symbol_name)

        # 找出 symbol 定義
        for item in symbol_index:
            if item.get("name") == symbol_name:
                symbol_hits.append(item)
                if "path" in item:
                    affected_files.add(item["path"])

        # 找出 symbol 引用
        for item in search_results:
            reference_hits.append(item)
            if "path" in item:
                affected_files.add(item["path"])

        # 風險等級評估（非常簡單版本）
        if len(affected_files) <= 2:
            risk_level = "low"
        elif len(affected_files) <= 6:
            risk_level = "medium"
        else:
            risk_level = "high"

        return {
            "symbol_name": symbol_name,
            "definitions": symbol_hits,
            "references": reference_hits,
            "affected_files": sorted(list(affected_files)),
            "risk_level": risk_level,
            "summary": (
                f"symbol '{symbol_name}' "
                f"定義 {len(symbol_hits)} 個，"
                f"引用 {len(reference_hits)} 個，"
                f"影響 {len(affected_files)} 個檔案。"
            ),
        }
