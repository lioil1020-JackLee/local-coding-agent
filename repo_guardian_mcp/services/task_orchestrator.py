
from __future__ import annotations

from typing import Any, Dict, List, Optional

from repo_guardian_mcp.services.edit_execution_orchestrator import (
    EditExecutionOrchestrator,
)


class TaskOrchestrator:
    '''
    任務總調度器（系統入口）。

    這個 class 是整個 coding agent 的「第一層入口」。

    設計目標：
    1. 分析與修改必須分離
    2. 分析模式不能改任何檔案
    3. 修改模式統一走安全 edit pipeline

    架構上：

        TaskOrchestrator
            ├─ analyze_repo()        ← 未來 agent 探索 repo 用
            └─ execute_edit()        ← 真正修改流程

    為了不破壞既有測試與工具 contract：
    run() 仍然維持原本參數順序。
    '''

    def __init__(self) -> None:
        # 第二層：安全修改執行器
        self._executor = EditExecutionOrchestrator()

    # ---------------------------------------------------------
    # 公開入口
    # ---------------------------------------------------------

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
        '''
        系統主入口。

        task_type:
            analyze → 只分析 repo
            edit    → 執行修改
        '''

        if task_type == "analyze":
            return self.analyze_repo(repo_root)

        if task_type == "edit":
            return self.execute_edit(
                repo_root=repo_root,
                relative_path=relative_path,
                content=content,
                mode=mode,
                old_text=old_text,
                operations=operations,
            )

        return {
            "ok": False,
            "error": f"unknown task_type: {task_type}",
        }

    # ---------------------------------------------------------
    # 分析模式（唯讀）
    # ---------------------------------------------------------

    def analyze_repo(self, repo_root: str) -> Dict[str, Any]:
        '''
        探索 repo 結構。

        未來 Cursor-like agent 會用這個能力：
        - 找檔案
        - 找入口點
        - 建立 repo context
        '''

        import os

        files: List[str] = []

        for root, _, filenames in os.walk(repo_root):
            for name in filenames:
                full_path = os.path.join(root, name)
                relative = os.path.relpath(full_path, repo_root)
                files.append(relative)

        files.sort()

        return {
            "ok": True,
            "mode": "analysis",
            "file_count": len(files),
            "files": files[:200],  # 避免回傳過大
        }

    # ---------------------------------------------------------
    # 修改模式
    # ---------------------------------------------------------

    def execute_edit(
        self,
        repo_root: str,
        relative_path: str,
        content: str,
        mode: str,
        old_text: Optional[str],
        operations: Optional[List[dict[str, Any]]],
    ) -> Dict[str, Any]:
        '''
        修改流程入口。

        所有真正修改 repo 的行為
        都必須透過 EditExecutionOrchestrator。
        '''

        return self._executor.run(
            repo_root=repo_root,
            relative_path=relative_path,
            content=content,
            mode=mode,
            old_text=old_text,
            operations=operations,
        )
