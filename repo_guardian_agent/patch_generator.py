"""
patch_generator

此模組封裝了使用補丁產生工具的邏輯。它負責將 Planner 提供的任務與上下文轉換成提案，並呼叫
repo_guardian_mcp 的 ``propose_patch`` 工具來產生結構化的補丁建議。
"""

from __future__ import annotations

from typing import Any, Dict, List

from repo_guardian_mcp.tools.propose_patch import propose_patch


def generate_patch(
    task: str,
    repo_root: str,
    relevant_paths: List[str] | None = None,
    readonly_paths: List[str] | None = None,
    context_snippets: List[str] | None = None,
    impact_summary: str | None = None,
    constraints: List[str] | None = None,
    max_files_to_change: int = 5,
    require_tests: bool = True,
    allow_new_files: bool = True,
) -> Dict[str, Any]:
    """
    產生結構化補丁提案。

    此函式會包裝 ``propose_patch`` 工具的呼叫，傳入各種參數，回傳標準化的結果字典。
    若產生提案失敗，錯誤訊息會包含在回傳值中。
    """
    return propose_patch(
        task=task,
        relevant_paths=relevant_paths or [],
        readonly_paths=readonly_paths or [],
        context_snippets=context_snippets or [],
        impact_summary=impact_summary,
        constraints=constraints or [],
        max_files_to_change=max_files_to_change,
        require_tests=require_tests,
        allow_new_files=allow_new_files,
        repo_root=repo_root,
    )