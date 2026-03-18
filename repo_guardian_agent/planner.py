"""
AgentPlanner

這個模組提供簡易的規劃器，將使用者的自然語言需求轉換成高階任務計劃。

在正式專案中，Planner 應該使用大語言模型理解指令並產生步驟清單；此實作僅提供一個範例，透過關鍵字判斷是分析還是修改任務。
"""

from __future__ import annotations

from typing import Any, Dict, List


class AgentPlanner:
    """
    代理層規劃器。

    此規劃器會根據自然語言輸入判斷任務類型，並在必要時呼叫補丁產生器
    或分析工具來提供更深入的規劃資訊。透過整合語言模型，planner
    可以為修改任務直接產生初步的補丁建議，方便後續流程使用。
    """

    def plan(self, user_request: str, repo_root: str) -> Dict[str, Any]:
        """
        根據使用者的自然語言需求產生任務計劃。

        參數：
            user_request (str): 使用者輸入的描述。
            repo_root (str): 專案根目錄路徑，供產生補丁時使用。

        回傳：
            dict: 內容包含 ``task_type`` 以及分析或修補結果的摘要。
        """
        text = (user_request or "").lower().strip()

        # 關鍵詞判斷：若包含修改相關字詞，視為修改任務
        edit_keywords = ["修改", "新增", "刪除", "編輯", "patch", "改一下", "調整"]
        if any(keyword in text for keyword in edit_keywords):
            # 產生修補提案
            try:
                from repo_guardian_agent.patch_generator import generate_patch

                patch_resp = generate_patch(task=user_request, repo_root=repo_root)
                return {
                    "task_type": "edit",
                    "patch_proposal": patch_resp,
                }
            except Exception as exc:  # 若補丁產生失敗，回傳錯誤資訊
                return {
                    "task_type": "edit",
                    "error": f"Failed to generate patch proposal: {exc}",
                }

        # 預設為分析任務：使用 run_task_pipeline 執行簡易分析
        try:
            from repo_guardian_mcp.tools.run_task_pipeline import run_task_pipeline

            analysis_result = run_task_pipeline(repo_root=repo_root, task_type="analyze")
            return {
                "task_type": "analyze",
                "analysis": analysis_result,
            }
        except Exception as exc:
            return {
                "task_type": "analyze",
                "error": f"Failed to analyze repository: {exc}",
            }