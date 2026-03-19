from __future__ import annotations

"""
task_orchestrator 服務層

這個模組負責協調高階任務，依據傳入的 task_type 來決定使用哪一個 Orchestrator。\
目前支援的任務有：

* ``edit``：修改檔案，調用 ``EditExecutionOrchestrator``。
* ``analyze``：分析 repo 目錄，回傳簡易檔案列表。

設計原則：

1. 對外維持既有 ``run()`` 合約，以繁體中文說明輸入與回傳內容。
2. 對內將修改邏輯下放給 ``EditExecutionOrchestrator``，未來如需其他任務可再拆分新的 orchestrator。
3. ``analyze_repo`` 僅做唯讀操作，不會修改任何檔案。
"""

from typing import Any, Dict, List, Optional

from repo_guardian_mcp.services.cli_agent_service import CLIAgentService
from repo_guardian_mcp.services.edit_execution_orchestrator import (
    EditExecutionOrchestrator,
)


class TaskOrchestrator:
    """
    任務總調度器（系統入口）。

    這個類別將不同的任務類型分派到對應的 orchestrator。對於編輯任務，它會使用
    ``EditExecutionOrchestrator`` 來執行修改管線；對於分析任務，則直接執行簡單的檔案遍歷。
    """

    def __init__(self) -> None:
        # 預先建立編輯任務的 orchestrator，以便重複使用
        self._executor = EditExecutionOrchestrator()
        self._cli_agent = CLIAgentService()

    def run(
        self,
        repo_root: str,
        relative_path: str = "README.md",
        content: str = "pipeline test",
        mode: str = "append",
        old_text: Optional[str] = None,
        operations: Optional[List[dict[str, Any]]] = None,
        task_type: str = "edit",
        user_request: str = "",
        session_id: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """
        執行指定的任務。

        參數：
            repo_root (str): 專案根目錄。
            relative_path (str): 要編輯的檔案相對路徑，僅限 ``edit`` 任務。
            content (str): 新增或替換的內容。
            mode (str): 編輯模式，``append``/``prepend``/``replace``。
            old_text (Optional[str]): 在 ``replace`` 模式下要被替換的舊文字。
            operations (Optional[List[dict]]): 複合編輯操作列表，支援一次處理多個片段。
            task_type (str): 任務類型，``edit`` 或 ``analyze``。

        回傳：
            dict: 結構化結果，包含 ``ok``(bool) 以及不同任務對應的欄位。
        """
        # 分派不同的任務類型
        if task_type == "analyze":
            return self.analyze_repo(repo_root)

        if task_type in {"agent", "auto"}:
            ctx = self._cli_agent.build_context(repo_root=repo_root, user_request=user_request, task_type=task_type, relative_path=relative_path, content=content, mode=mode, old_text=old_text, operations=operations, session_id=session_id, metadata=dict(metadata or {}))
            return self._cli_agent.run(ctx)

        if task_type != "edit":
            # 未知任務類型，回傳錯誤
            return {
                "ok": False,
                "error": f"unknown task_type: {task_type}",
            }

        # 編輯任務：委派給 EditExecutionOrchestrator
        return self._executor.run(
            repo_root=repo_root,
            relative_path=relative_path,
            content=content,
            mode=mode,
            old_text=old_text,
            operations=operations,
        )

    def analyze_repo(self, repo_root: str) -> Dict[str, Any]:
        """
        簡易分析指定的專案目錄。

        這個方法會遞迴列出 repo 內的檔案，回傳檔案總數與前 200 個檔案路徑。它不會寫入或修改任何檔案。

        參數：
            repo_root (str): 專案根目錄。

        回傳：
            dict: 結構化結果，包含 ``ok``、``mode``、``file_count`` 與 ``files``。
        """
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