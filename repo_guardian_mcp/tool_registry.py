from __future__ import annotations

from importlib import import_module
from typing import Any, Callable


TOOLS: dict[str, str] = {}


def register(name: str, target: str) -> None:
    """註冊一個工具函式的匯入路徑。"""
    TOOLS[name] = target


def get_tool(name: str) -> Callable[..., Any]:
    """依名稱取得工具函式（lazy import）。"""
    if name not in TOOLS:
        raise KeyError(f"找不到工具: {name}")

    target = TOOLS[name]

    try:
        module_path, fn_name = target.split(":", 1)
    except ValueError as exc:
        raise ValueError(f"工具註冊格式錯誤: {target}") from exc

    module = import_module(module_path)

    try:
        fn = getattr(module, fn_name)
    except AttributeError as exc:
        raise AttributeError(f"模組 {module_path} 中找不到函式 {fn_name}") from exc

    return fn


def list_tools() -> list[str]:
    """列出目前已註冊的工具名稱。"""
    return sorted(TOOLS.keys())


# ------------------------------
# Tool registrations
# ------------------------------

# 基本 repo 工具
register("get_repo_overview", "repo_guardian_mcp.tools.repo_overview:repo_overview")
register("get_entrypoints", "repo_guardian_mcp.tools.find_entrypoints:find_entrypoints")
register("search_codebase", "repo_guardian_mcp.tools.search_code:search_code")
register("get_symbol_index", "repo_guardian_mcp.tools.symbol_index:symbol_index")
register("get_code_region", "repo_guardian_mcp.tools.read_code_region:read_code_region")
register("git_status_plus", "repo_guardian_mcp.tools.git_status_plus:git_status_plus")

# planning
register("plan_change", "repo_guardian_mcp.tools.plan_change:plan_change")
register("get_impact_analysis", "repo_guardian_mcp.tools.impact_analysis:impact_analysis")

# patch workflow
register("propose_patch", "repo_guardian_mcp.tools.propose_patch:propose_patch")
register("preview_diff", "repo_guardian_mcp.tools.preview_diff:preview_diff")
register("stage_patch", "repo_guardian_mcp.tools.stage_patch:stage_patch")