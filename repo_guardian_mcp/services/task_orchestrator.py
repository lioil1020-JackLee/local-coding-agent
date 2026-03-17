from __future__ import annotations

from typing import Any, Dict, List, Optional

from repo_guardian_mcp.services.edit_execution_orchestrator import (
    EditExecutionOrchestrator,
)


class TaskOrchestrator:
    '''
    任務總調度器（系統入口）。

    設計原則：
    - 對外維持既有 run() contract
    - 對內把真正的修改流程下放給 EditExecutionOrchestrator
    - 後續分析 / 修改可以繼續往不同 orchestrator 分層
    '''

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
        task_type: str = "edit",
    ) -> Dict[str, Any]:
        if task_type == "analyze":
            return self.analyze_repo(repo_root)

        if task_type != "edit":
            return {
                "ok": False,
                "error": f"unknown task_type: {task_type}",
            }

        return self._executor.run(
            repo_root=repo_root,
            relative_path=relative_path,
            content=content,
            mode=mode,
            old_text=old_text,
            operations=operations,
        )

    def analyze_repo(self, repo_root: str) -> Dict[str, Any]:
        import os

        files: List[str] = []
        for root, _, filenames in os.walk(repo_root):
            for name in filenames:
                files.append(os.path.relpath(os.path.join(root, name), repo_root))

        files.sort()
        return {
            "ok": True,
            "mode": "analysis",
            "file_count": len(files),
            "files": files[:200],
        }
