from __future__ import annotations

from pathlib import Path

from repo_guardian_mcp.models import RepoOverviewResult
from repo_guardian_mcp.services.repo_scan_service import RepoScanService


def repo_overview(workspace_root: Path) -> RepoOverviewResult:
    """掃描專案並輸出基本資訊。"""
    service = RepoScanService(workspace_root)
    return service.scan()