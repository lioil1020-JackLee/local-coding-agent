
from __future__ import annotations

from typing import Any, Dict, List, Optional

from repo_guardian_mcp.services.task_orchestrator import TaskOrchestrator


def run_task_pipeline(
    repo_root: str,
    relative_path: str = "README.md",
    content: str = "pipeline test",
    mode: str = "append",
    old_text: Optional[str] = None,
    operations: Optional[List[dict[str, Any]]] = None,
) -> Dict[str, Any]:
    """
    Repo Guardian 安全編輯 pipeline（Phase 1）

    流程：
    1. 建立 sandbox session
    2. 套用修改（單檔或 operations）
    3. 產生 diff
    4. 執行 validation
    5. 回傳 pipeline 結果

    此 function 是 MCP tool 的入口點。
    真正的流程邏輯在 TaskOrchestrator。
    """

    if not repo_root:
        return {
            "ok": False,
            "error": "repo_root is empty",
        }

    orchestrator = TaskOrchestrator()

    try:
        result = orchestrator.run(
            repo_root=repo_root,
            relative_path=relative_path,
            content=content,
            mode=mode,
            old_text=old_text,
            operations=operations,
        )

        return {
            "ok": True,
            "pipeline": "repo_guardian_task_pipeline",
            "result": result,
        }

    except Exception as e:
        return {
            "ok": False,
            "pipeline": "repo_guardian_task_pipeline",
            "error": str(e),
            "repo_root": repo_root,
            "relative_path": relative_path,
            "mode": mode,
        }
