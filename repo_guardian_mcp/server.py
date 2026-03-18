"""
repo_guardian_mcp.server

FastAPI MCP server skeleton。

這個模組提供一個簡易的 MCP server 實作，註冊兩個主要端點：

* ``/run_task_pipeline``：呼叫 ``run_task_pipeline`` 工具執行 edit 或分析任務。
* ``/tools/{name}``：泛用工具端點，根據名稱呼叫任意 MCP 工具。

使用方式：

```bash
uvicorn repo_guardian_mcp.server:app --reload --port 8000
```

然後透過 HTTP POST 請求呼叫對應端點即可。此 server 僅作為示範，
正式部署時可加入認證、日誌等功能。
"""

from __future__ import annotations

from typing import Any, Dict

from fastapi import FastAPI, HTTPException, Request, Response
from pydantic import BaseModel

from repo_guardian_mcp.tool_registry import get_tool

import logging
import os

# 設定簡易日誌：將日誌寫入指定檔案，預設路徑為 agent_runtime/mcp_server.log
_log_path = os.getenv("MCP_LOG_FILE")
if not _log_path:
    # 將日誌存放於專案根目錄下的 agent_runtime
    workspace_root = os.getenv("REPO_GUARDIAN_WORKSPACE_ROOT", os.getcwd())
    _log_path = os.path.join(workspace_root, "agent_runtime", "mcp_server.log")
os.makedirs(os.path.dirname(_log_path), exist_ok=True)
logging.basicConfig(
    level=logging.INFO,
    filename=_log_path,
    format="%(asctime)s %(levelname)s %(message)s",
    encoding="utf-8",
)

# API 金鑰，用於簡單的身份驗證。若未設定，則允許任何請求。
_api_key = os.getenv("MCP_API_KEY")

@app.middleware("http")
async def auth_and_logging_middleware(request: Request, call_next):
    """中介層：檢查 API 金鑰並記錄日誌。"""
    # 檢查金鑰（僅對 /run_task_pipeline 與 /tools 路由）
    if request.url.path.startswith("/run_task_pipeline") or request.url.path.startswith("/tools"):
        if _api_key:
            # 從標頭讀取 X-API-Key
            provided_key = request.headers.get("X-API-Key")
            if provided_key != _api_key:
                # 未授權
                return Response(status_code=401, content="Unauthorized")
    # 呼叫內部處理器
    response = await call_next(request)
    # 日誌：紀錄方法、路徑與狀態碼
    logging.info(f"{request.method} {request.url.path} -> {response.status_code}")
    return response


app = FastAPI(title="Local Coding Agent MCP")


class TaskRequest(BaseModel):
    repo_root: str
    relative_path: str = "README.md"
    content: str = ""
    mode: str = "append"
    old_text: str | None = None
    operations: list[dict[str, Any]] | None = None
    task_type: str = "edit"


@app.get("/")
async def root() -> Dict[str, Any]:
    """Health check endpoint。"""
    return {"ok": True, "message": "MCP server is running"}


@app.post("/run_task_pipeline")
async def run_task(request: TaskRequest) -> Any:
    """
    執行指定任務的 pipeline。

    request.task_type 可為 "edit" 或 "analyze"，其餘欄位為編輯任務所需參數。
    若執行失敗，會回傳 4xx 錯誤。
    """
    tool = get_tool("run_task_pipeline")
    result = tool(
        repo_root=request.repo_root,
        relative_path=request.relative_path,
        content=request.content,
        mode=request.mode,
        old_text=request.old_text,
        operations=request.operations,
        task_type=request.task_type,
    )
    if not isinstance(result, dict) or not result.get("ok", False):
        raise HTTPException(status_code=400, detail=result.get("error", "run_task_pipeline failed"))
    return result


@app.post("/tools/{name}")
async def call_tool_endpoint(name: str, args: Dict[str, Any]) -> Any:
    """
    呼叫指定的 MCP 工具。

    Args:
        name: 工具名稱，必須存在於 tool_registry 中。
        args: dict 形式的工具參數。

    Returns:
        工具的結果，如果呼叫失敗則拋出 HTTPException。
    """
    try:
        tool = get_tool(name)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    try:
        result = tool(**(args or {}))
    except TypeError as exc:
        # 傳入參數不符合工具簽名
        raise HTTPException(status_code=400, detail=f"Invalid arguments for {name}: {exc}") from exc
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(status_code=500, detail=f"Tool {name} failed: {exc}") from exc
    return result