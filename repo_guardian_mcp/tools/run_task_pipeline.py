from __future__ import annotations

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
) -> Dict[str, Any]:
    """
    執行 repo_guardian 的主修改流程。

    這個版本保留既有的 flat contract：
    - session_id 在最外層
    - diff_text / validation / summary 都在最外層
    - 只額外補 timing 方便看耗時
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
        )
        orchestrator_seconds = round(time.time() - orchestrator_start, 3)
        total_seconds = round(time.time() - start_time, 3)

        if not isinstance(result, dict):
            return {
                "ok": False,
                "pipeline": "repo_guardian_task_pipeline",
                "error": "TaskOrchestrator.run() 回傳格式錯誤",
                "timing": {
                    "orchestrator_seconds": orchestrator_seconds,
                    "total_seconds": total_seconds,
                },
            }

        # 關鍵：保留原本 flat contract，不要把結果包進 result 裡
        response: Dict[str, Any] = {
            "ok": True,
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