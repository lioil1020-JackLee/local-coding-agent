from __future__ import annotations

from pathlib import Path

from repo_guardian_mcp.services.planning_service import PlanningService


def impact_analysis(workspace_root: Path, symbol_name: str) -> dict:
    """分析指定 symbol 在目前 repo 中的影響範圍。"""
    service = PlanningService(workspace_root)
    return service.impact_analysis(symbol_name)