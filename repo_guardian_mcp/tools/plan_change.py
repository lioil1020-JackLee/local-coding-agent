from __future__ import annotations

from typing import Dict, List


def analyze(change: Dict) -> Dict:
    """
    Plan Change v1

    在真正修改程式碼前，先產生一份修改計畫。

    回傳內容：
    - target_file
    - description
    - affected_files
    - risk_level
    - recommended_pipeline
    """

    target_file = change.get("file")
    description = change.get("description", "")
    affected_files: List[str] = change.get("affected_files", [])

    if not target_file:
        return {
            "ok": False,
            "error": "change['file'] is required"
        }

    # 簡單風險評估
    if len(affected_files) <= 1:
        risk_level = "low"
    elif len(affected_files) <= 5:
        risk_level = "medium"
    else:
        risk_level = "high"

    plan = {
        "target_file": target_file,
        "description": description,
        "affected_files": affected_files,
        "risk_level": risk_level,
        "recommended_pipeline": [
            "impact_analysis",
            "plan_change",
            "run_task_pipeline"
        ]
    }

    return {
        "ok": True,
        "plan": plan
    }
