"""
repo_guardian_mcp.server

這個模組提供一個簡易的 Model Context Protocol (MCP) 伺服器實作，
透過標準輸入與標準輸出與客戶端進行 JSON-RPC 2.0 通訊。此伺服器
實作了初始化、列出工具以及呼叫工具的基本功能，足以供 VS Code
Continue 等支援 MCP 的 IDE 擴充自動發現與調用工具。為了最大
程度簡化部署，伺服器不依賴外部套件，只使用 Python 標準函式庫。

伺服器流程簡述：

1. 從 stdin 持續讀取一行 JSON 字串，解析為請求物件。
2. 根據請求中的 `method` 處理不同的 RPC：
   * `initialize`：回傳支援的協定版本與能力。
   * `tools/list`：回傳所有已註冊工具的名稱、說明與輸入模式(schema)。
   * `tools/call`：依名稱取得工具函式，傳入參數執行並回傳結果。
   * `ping`：回傳空物件以保持連線存活。
3. 將回應物件寫入 stdout（附帶 id），每個回應占一行。

若需要啟動 HTTP 伺服器供手動調用，可將環境變數 `MCP_HTTP` 設為
`1`，此時會啟動一個簡易 FastAPI 伺服器，保留原有的 REST API。建議
在整合 VS Code Continue 等 IDE 時使用預設 STDIO 模式。

注意：此實作僅覆蓋 MCP 核心功能，不支援資源、提示等進階
協定訊息，後續如有需要可延伸。
"""

from __future__ import annotations

import inspect
import json
import os
import sys
import logging
import time
import uuid
from typing import Any, Callable, Dict, List

# 導入工具註冊表
from repo_guardian_mcp.tool_registry import get_tool, list_tools, TOOLS

__all__ = ["main"]


JSONRPC_PARSE_ERROR = -32700
JSONRPC_INVALID_REQUEST = -32600
JSONRPC_METHOD_NOT_FOUND = -32601
JSONRPC_INVALID_PARAMS = -32602
JSONRPC_INTERNAL_ERROR = -32603


class MCPProtocolError(RuntimeError):
    def __init__(self, message: str, *, code: int = JSONRPC_INTERNAL_ERROR, data: dict[str, Any] | None = None) -> None:
        super().__init__(message)
        self.code = code
        self.data = dict(data or {})


def _python_type_to_json_schema(py_type: Any) -> str:
    """將 Python 型別映射為 JSON Schema 基本型別。"""
    # 使用字串比較以避免遞迴導致型別不明
    type_str = str(py_type)
    if py_type in (str, bytes):
        return "string"
    if py_type in (int, float):
        return "number"
    if py_type is bool:
        return "boolean"
    if type_str.startswith("typing.List") or type_str.startswith("list["):
        return "array"
    if type_str.startswith("typing.Dict") or type_str.startswith("dict["):
        return "object"
    # 預設皆為字串
    return "string"


def _build_input_schema(func: Callable) -> Dict[str, Any]:
    """根據函式簽名產生簡易的 JSON Schema。"""
    sig = inspect.signature(func)
    properties: Dict[str, Any] = {}
    required: List[str] = []
    for name, param in sig.parameters.items():
        # 參數 type 轉為 JSON Schema 型別
        annotation = param.annotation
        json_type = _python_type_to_json_schema(annotation)
        properties[name] = {"type": json_type}
        if param.default is inspect.Parameter.empty:
            required.append(name)
    schema: Dict[str, Any] = {"type": "object", "properties": properties}
    if required:
        schema["required"] = required
    return schema


def _prepare_tools_metadata() -> List[Dict[str, Any]]:
    """讀取註冊表並產生工具清單，每個工具包含名稱、描述與輸入 schema。"""
    tools_meta: List[Dict[str, Any]] = []
    for name in list_tools():
        try:
            func = get_tool(name)
        except Exception:
            # 忽略無法匯入的工具
            continue
        # 以函式註解或 docstring 作為描述
        description = (inspect.getdoc(func) or "無描述").strip()
        # 保留繁體中文描述，避免 MCP tools metadata 失真。
        description = description or "無描述"
        try:
            input_schema = _build_input_schema(func)
        except Exception:
            input_schema = {"type": "object"}
        tools_meta.append({
            "name": name,
            "description": description,
            "inputSchema": input_schema,
        })
    return tools_meta


def _send_response(response: Dict[str, Any]) -> None:
    """將回應物件以 JSON 格式寫入 stdout。"""
    sys.stdout.write(json.dumps(response, ensure_ascii=False) + "\n")
    sys.stdout.flush()


def _handle_initialize(request: Dict[str, Any]) -> Dict[str, Any]:
    """處理 initialize 請求，回傳協定版本與能力。"""
    params = request.get("params", {}) or {}
    protocol_version = params.get("protocolVersion", "2024-11-05")
    # 回報本伺服器提供 tools 功能，其餘能力可按需擴充
    result = {
        "protocolVersion": protocol_version,
        "capabilities": {
            "tools": {},
        },
        "serverInfo": {
            "name": "repo_guardian",
            "version": "0.1.0",
        },
    }
    return result


def _handle_tools_list() -> Dict[str, Any]:
    """回傳工具清單。"""
    return {"tools": _prepare_tools_metadata()}


def _handle_tools_call(request: Dict[str, Any]) -> Dict[str, Any]:
    """呼叫指定工具並回傳結果。"""
    params = request.get("params", {}) or {}
    tool_name = params.get("name")
    arguments = params.get("arguments") or {}
    if not isinstance(tool_name, str) or not tool_name.strip():
        raise MCPProtocolError("tools/call 缺少 name 參數", code=JSONRPC_INVALID_PARAMS)
    if not isinstance(arguments, dict):
        raise MCPProtocolError("tools/call arguments 必須為 object", code=JSONRPC_INVALID_PARAMS)
    try:
        func = get_tool(tool_name)
    except Exception:
        raise MCPProtocolError(f"Tool {tool_name} not found", code=JSONRPC_INVALID_PARAMS)
    # 執行工具，捕捉任何例外並轉為錯誤
    result_obj: Any
    started = time.time()
    try:
        result_obj = func(**arguments)
    except Exception as exc:  # noqa: BLE001
        raise MCPProtocolError(
            f"Tool {tool_name} failed: {exc}",
            code=JSONRPC_INTERNAL_ERROR,
            data={"tool_name": tool_name},
        )
    elapsed_ms = int((time.time() - started) * 1000)
    trace_ref = f"mcp-tool-{int(time.time() * 1000)}-{uuid.uuid4().hex[:8]}"
    # MCP 規範中，result 應包含 content (文字或結構化)。這裡將原始結果
    # 序列化為 JSON 字串回傳，讓客戶端自行解析。
    try:
        content_text = json.dumps(result_obj, ensure_ascii=False)
    except Exception:
        # 若結果無法序列化為 JSON，使用 repr() 退而求其次
        content_text = repr(result_obj)
    return {
        "content": [
            {
                "type": "text",
                "text": content_text,
            }
        ],
        "structuredContent": {
            "ok": True,
            "tool_name": tool_name,
            "trace_ref": trace_ref,
            "timing_ms": elapsed_ms,
            "result": result_obj,
        },
    }


def _handle_request(request: Dict[str, Any]) -> Dict[str, Any]:
    """根據請求方法分派處理器，回傳回應結果或拋出例外。"""
    if not isinstance(request, dict):
        raise MCPProtocolError("Request must be a JSON object", code=JSONRPC_INVALID_REQUEST)
    method = request.get("method")
    if not isinstance(method, str) or not method.strip():
        raise MCPProtocolError("Request missing method", code=JSONRPC_INVALID_REQUEST)
    if method == "initialize":
        return _handle_initialize(request)
    if method == "tools/list":
        return _handle_tools_list()
    if method == "tools/call":
        return _handle_tools_call(request)
    if method == "ping":
        return {}
    # 未支援的方法
    raise MCPProtocolError(f"Unsupported method: {method}", code=JSONRPC_METHOD_NOT_FOUND)


def _build_error_response(*, request_id: Any, code: int, message: str, data: dict[str, Any] | None = None) -> Dict[str, Any]:
    payload: Dict[str, Any] = {
        "jsonrpc": "2.0",
        "id": request_id,
        "error": {
            "code": code,
            "message": message,
        },
    }
    if data:
        payload["error"]["data"] = data
    return payload


def main() -> None:
    """STDIO MCP 伺服器主迴圈。讀取請求並回傳回應。"""
    # 如果環境變數 MCP_HTTP 為 "1"，啟動 HTTP 伺服器以便手動調試
    if os.getenv("MCP_HTTP") == "1":
        # 避免於無外部套件時導致匯入錯誤
        try:
            from fastapi import FastAPI, HTTPException
            import uvicorn
        except Exception:
            print("FastAPI or uvicorn not installed, falling back to stdio server.")
        else:
            app = FastAPI(title="Repo Guardian MCP (HTTP)")

            @app.post("/mcp")
            async def call_mcp(request_body: Dict[str, Any]) -> Any:
                """簡易 HTTP 端點：接收單一 MCP 請求並回傳回應。"""
                _id = request_body.get("id")
                try:
                    result = _handle_request(request_body)
                    return {"jsonrpc": "2.0", "id": _id, "result": result}
                except Exception as exc:  # noqa: BLE001
                    return {
                        "jsonrpc": "2.0",
                        "id": _id,
                        "error": {"code": -32603, "message": str(exc)},
                    }

            # 啟動 Uvicorn 伺服器
            port = int(os.getenv("PORT", "8000"))
            uvicorn.run(app, host="0.0.0.0", port=port)
            return

    # STDIO 模式
    # 設定簡易日誌到 agent_runtime/mcp_server.log
    workspace_root = os.getenv("REPO_GUARDIAN_WORKSPACE_ROOT", os.getcwd())
    log_path = os.path.join(workspace_root, "agent_runtime", "mcp_server.log")
    os.makedirs(os.path.dirname(log_path), exist_ok=True)
    logging.basicConfig(
        level=logging.INFO,
        filename=log_path,
        format="%(asctime)s %(levelname)s %(message)s",
        encoding="utf-8",
    )
    # 主迴圈：逐行處理請求
    for line in sys.stdin:
        line = line.strip()
        if not line:
            continue
        try:
            request = json.loads(line)
        except json.JSONDecodeError:
            _send_response(
                _build_error_response(
                    request_id=None,
                    code=JSONRPC_PARSE_ERROR,
                    message="Invalid JSON payload",
                )
            )
            continue
        response: Dict[str, Any] = {"jsonrpc": "2.0"}
        _id = request.get("id")
        if _id is not None:
            response["id"] = _id
        try:
            result = _handle_request(request)
            response["result"] = result
        except MCPProtocolError as exc:
            response = _build_error_response(
                request_id=_id,
                code=exc.code,
                message=str(exc),
                data=exc.data if exc.data else None,
            )
        except Exception as exc:  # noqa: BLE001
            response = _build_error_response(
                request_id=_id,
                code=JSONRPC_INTERNAL_ERROR,
                message=str(exc),
            )
            # 錯誤記錄
            logging.error(f"Error processing request: {exc}")
        _send_response(response)


if __name__ == "__main__":  # pragma: no cover
    main()
