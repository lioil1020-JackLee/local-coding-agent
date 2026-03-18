"""
validation_controller

此模組提供驗證控制器，用於在套用補丁後執行各種驗證。

目前僅呼叫 repo_guardian_mcp 的 ``run_validation_pipeline`` 工具，但可在此處擴充
其他驗證，例如靜態分析或單元測試等。
"""

from __future__ import annotations

from typing import Any, Dict

from repo_guardian_mcp.tools.run_validation_pipeline import run_validation_pipeline


def validate_patch(repo_root: str, session_id: str) -> Dict[str, Any]:
    """
    執行完整的驗證流程，包括：

    1. 呼叫 MCP 的 ``run_validation_pipeline`` 工具，產生 diff 與基本檢查。
    2. 在檢查通過後，進一步執行靜態分析（語法檢查）以及單元測試。
    3. 回傳整合的驗證結果。

    參數：
        repo_root (str): 專案根目錄，用於執行測試與分析。
        session_id (str): 要驗證的 session ID。

    回傳：
        dict: 包含驗證狀態、檢查列表與摘要的結構化資料。
    """
    # 先執行 MCP 提供的驗證管線
    result: Dict[str, Any] = run_validation_pipeline(repo_root=repo_root, session_id=session_id)

    # 如果基本驗證已失敗或沒有預期欄位，直接回傳
    if not isinstance(result, dict) or not result.get("status") or result.get("status") != "pass":
        return result

    # 初始化 checks 列表以方便新增項目
    checks = result.get("checks", [])

    # 嘗試從 diff 內容推斷變更檔案，以執行靜態分析
    changed_files: list[str] = []
    diff_text = result.get("diff_text", "")
    if diff_text:
        for line in diff_text.splitlines():
            # unified diff 內以 "+++<space>path" 表示修改後的檔案
            if line.startswith("+++ "):
                parts = line.split(maxsplit=1)
                if len(parts) == 2:
                    path = parts[1].strip()
                    # 避免以 a/ b/ 格式開頭
                    if path.startswith("b/"):
                        path = path[2:]
                    changed_files.append(path)

    # 執行靜態語法檢查：僅對 Python 檔案進行
    static_ok = True
    static_errors: list[str] = []
    import os
    for rel_path in changed_files:
        if rel_path.endswith(".py"):
            abs_path = os.path.join(repo_root, rel_path)
            try:
                source_code = open(abs_path, "r", encoding="utf-8").read()
                compile(source_code, abs_path, "exec")
            except Exception as exc:
                static_ok = False
                static_errors.append(f"{rel_path}: {exc}")

    if static_ok:
        checks.append({
            "name": "static_analysis",
            "status": "pass",
            "message": "靜態分析（語法檢查）通過。",
        })
    else:
        checks.append({
            "name": "static_analysis",
            "status": "fail",
            "message": "靜態分析失敗：\n" + "\n".join(static_errors),
        })
        result["status"] = "fail"
        result["passed"] = False

    # 若靜態分析沒問題，執行單元測試
    if result.get("status") == "pass":
        import subprocess
        try:
            proc = subprocess.run(
                ["pytest", "-q"], cwd=repo_root, capture_output=True, text=True
            )
            if proc.returncode == 0:
                checks.append({
                    "name": "unit_tests",
                    "status": "pass",
                    "message": "所有單元測試通過。",
                })
            else:
                checks.append({
                    "name": "unit_tests",
                    "status": "fail",
                    "message": proc.stdout + proc.stderr,
                })
                result["status"] = "fail"
                result["passed"] = False
        except Exception as exc:
            checks.append({
                "name": "unit_tests",
                "status": "error",
                "message": f"執行 pytest 時發生例外：{exc}",
            })
            # 視為驗證失敗
            result["status"] = "fail"
            result["passed"] = False

    # 更新 result 的 checks 列表
    result["checks"] = checks

    return result