from __future__ import annotations

import os
from pathlib import Path
from pydantic import BaseModel


class Settings(BaseModel):
    """系統設定。"""

    workspace_root: Path
    runtime_root: Path
    sessions_root: Path
    logs_root: Path
    snapshots_root: Path
    sandbox_root: Path

    @classmethod
    def load(cls) -> "Settings":
        """從環境變數載入設定。"""
        workspace_root = Path(
            os.environ.get("REPO_GUARDIAN_WORKSPACE_ROOT", ".")
        ).resolve()

        runtime_root = workspace_root / "agent_runtime"

        return cls(
            workspace_root=workspace_root,
            runtime_root=runtime_root,
            sessions_root=runtime_root / "sessions",
            logs_root=runtime_root / "logs",
            snapshots_root=runtime_root / "snapshots",
            sandbox_root=runtime_root / "sandbox_worktrees",
        )