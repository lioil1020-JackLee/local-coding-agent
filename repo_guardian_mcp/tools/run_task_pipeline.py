from __future__ import annotations

"""
run_task_pipeline 工具

此工具是 repo_guardian 的主要入口點，用於執行修改或分析流程。它會呼叫
``TaskOrchestrator`` 的 ``run()`` 方法，並在回傳結果中補上執行耗時，方便
診斷效能。工具保持扁平化 contract：所有重要欄位（如 session_id、diff_text、
validation）都會出現在最外層，而不是包在巢狀結構裡。
"""

import time
from typing import Any, Dict, List, Optional

from repo_guardian_mcp.services.task_orchestrator import TaskOrchestrator


def run_task_pipeline(
    repo_root: str,
    relative_path: str = "README.md",
    content: str = "",
    mode: str = "append",
    old_text: Optional[str] = None,
    operations: Optional[List[dict[str, Any]]] = None,
    task_type: str = "edit",
) -> Dict[str, Any]:
    """
    執行 repo_guardian 的主修改或分析流程。

    參數：
        repo_root (str): 專案根目錄。
        relative_path (str): 要編輯的檔案相對路徑，僅在 ``edit`` 任務下需要。
        content (str): 新增或替換的內容。
        mode (str): 編輯模式，``append``、``prepend`` 或 ``replace``。
        old_text (Optional[str]): 舊文字，僅在 ``replace`` 模式使用。
        operations (Optional[List[dict]]): 複合編輯操作列表。
        task_type (str): 任務類型，``edit`` 或 ``analyze``。

    回傳：
        dict: 包含 ``ok``、``pipeline``、``timing`` 以及任務特有欄位的字典。
    """
    start_time = time.time()

    try:
        orchestrator = TaskOrchestrator()

        orchestrator_start = time.time()
        result = orchestrator.run(
            repo_root=repo_root,
            relative_path=relative_path,
            content=content,
            mode=mode,
            old_text=old_text,
            operations=operations,
            task_type=task_type,
        )
        orchestrator_seconds = round(time.time() - orchestrator_start, 3)
        total_seconds = round(time.time() - start_time, 3)

        if not isinstance(result, dict):
            # 確保回傳格式正確
            return {
                "ok": False,
                "pipeline": "repo_guardian_task_pipeline",
                "error": "TaskOrchestrator.run() 回傳格式錯誤",
                "timing": {
                    "orchestrator_seconds": orchestrator_seconds,
                    "total_seconds": total_seconds,
                },
            }

        # 保持扁平化 contract，不將資料包進 result 裡
        response: Dict[str, Any] = {
            "pipeline": "repo_guardian_task_pipeline",
            **result,
            "timing": {
                "orchestrator_seconds": orchestrator_seconds,
                "total_seconds": total_seconds,
            },
        }
        return response

    except Exception as exc:
        total_seconds = round(time.time() - start_time, 3)
        return {
            "ok": False,
            "pipeline": "repo_guardian_task_pipeline",
            "error": str(exc),
            "timing": {
                "total_seconds": total_seconds,
            },
        }