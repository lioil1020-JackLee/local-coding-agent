from __future__ import annotations

from typing import Any, Dict, List, Optional

from repo_guardian_mcp.services.edit_execution_orchestrator import (
    EditExecutionOrchestrator,
)


class TaskOrchestrator:
    """
    相容層。

    對外仍保留既有 `TaskOrchestrator.run()` 介面，
    但內部正式改由 `EditExecutionOrchestrator` 執行。

    這樣可以先完成責任拆分，
    又不會一下子打壞既有 tool / test contract。
    """

    def __init__(self) -> None:
        self._executor = EditExecutionOrchestrator()

    def run(
        self,
        repo_root: str,
        relative_path: str = "README.md",
        content: str = "pipeline test",
        mode: str = "append",
        old_text: Optional[str] = None,
        operations: Optional[List[dict[str, Any]]] = None,
    ) -> Dict[str, Any]:
        return self._executor.run(
            repo_root=repo_root,
            relative_path=relative_path,
            content=content,
            mode=mode,
            old_text=old_text,
            operations=operations,
        )
