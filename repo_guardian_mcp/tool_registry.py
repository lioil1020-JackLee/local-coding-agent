from __future__ import annotations

"""
tool_registry

這個模組維護 MCP 工具的註冊表，將工具名稱映射到具體的模組與函式。其他
程式碼可以透過 ``get_tool`` 依名稱取得對應的函式並執行。為了降低耦合，工具
的匯入採延遲導入：只有當實際調用時才匯入目標模組。

若需要新增或刪除工具，請更新此註冊表。未實作的工具不應註冊，以免在調用
時導致匯入錯誤。
"""

from importlib import import_module
from typing import Callable


# 工具註冊表：名稱對應到 "模組路徑:函式名稱"
TOOLS: dict[str, str] = {}


def register(name: str, target: str) -> None:
    """註冊工具名稱與其目標模組/函式。"""
    TOOLS[name] = target


def get_tool(name: str) -> Callable:
    """根據名稱取得對應的工具函式。若不存在則拋出 KeyError。"""
    if name not in TOOLS:
        raise KeyError(f"Tool not found: {name}")

    module_path, func_name = TOOLS[name].split(":")
    module = import_module(module_path)
    return getattr(module, func_name)


def list_tools() -> list[str]:
    """列出所有已註冊的工具名稱。"""
    return sorted(TOOLS.keys())


# ==== 工具註冊區 ====
# repo analysis / inspection
register("analyze_repo", "repo_guardian_mcp.tools.analyze_repo:analyze_repo")
register("find_entrypoints", "repo_guardian_mcp.tools.find_entrypoints:find_entrypoints")
register("get_session_status", "repo_guardian_mcp.tools.get_session_status:get_session_status")

# sandbox session workflow
register("create_task_session", "repo_guardian_mcp.tools.create_task_session:create_task_session")
register("preview_session_diff", "repo_guardian_mcp.tools.preview_session_diff:preview_session_diff")
register("run_validation_pipeline", "repo_guardian_mcp.tools.run_validation_pipeline:run_validation_pipeline")
register("rollback_session", "repo_guardian_mcp.tools.rollback_session:rollback_session")

# main pipeline
register("run_task_pipeline", "repo_guardian_mcp.tools.run_task_pipeline:run_task_pipeline")

# 讀取與搜尋程式碼
register("search_codebase", "repo_guardian_mcp.tools.search_code:search_code")
register("get_code_region", "repo_guardian_mcp.tools.read_code_region:read_code_region")
register("get_repo_overview", "repo_guardian_mcp.tools.repo_overview:repo_overview")

# patch 相關工具
register("propose_patch", "repo_guardian_mcp.tools.propose_patch:propose_patch")
register("preview_diff", "repo_guardian_mcp.tools.preview_diff:preview_diff")
register("stage_patch", "repo_guardian_mcp.tools.stage_patch:stage_patch")

# 高階重構工具
register("move_file", "repo_guardian_mcp.tools.move_file:move_file")