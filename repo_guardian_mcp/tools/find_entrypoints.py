from __future__ import annotations

from pathlib import Path

from repo_guardian_mcp.services.entrypoint_service import EntrypointService


def find_entrypoints(workspace_root: Path) -> list[str]:
    """找出專案中可能的入口點。"""
    service = EntrypointService(workspace_root)
    return service.find_entrypoints()