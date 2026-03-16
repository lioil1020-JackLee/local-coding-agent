from __future__ import annotations

from importlib import import_module
from typing import Callable


TOOLS: dict[str, str] = {}


def register(name: str, target: str) -> None:
    TOOLS[name] = target


def get_tool(name: str) -> Callable:
    if name not in TOOLS:
        raise KeyError(f"Tool not found: {name}")

    module_path, func_name = TOOLS[name].split(":")
    module = import_module(module_path)
    return getattr(module, func_name)


def list_tools() -> list[str]:
    return sorted(TOOLS.keys())


# repo analysis / inspection
register("get_repo_overview", "repo_guardian_mcp.tools.repo_overview:repo_overview")
register("get_entrypoints", "repo_guardian_mcp.tools.find_entrypoints:find_entrypoints")
register("search_codebase", "repo_guardian_mcp.tools.search_code:search_code")
register("get_code_region", "repo_guardian_mcp.tools.read_code_region:read_code_region")
register("get_impact_analysis", "repo_guardian_mcp.tools.impact_analysis:impact_analysis")
register("get_symbol_index", "repo_guardian_mcp.tools.symbol_index:symbol_index")
register("git_status_plus", "repo_guardian_mcp.tools.git_status_plus:git_status_plus")

# patch workflow
register("plan_change", "repo_guardian_mcp.tools.plan_change:analyze")
register("propose_patch", "repo_guardian_mcp.tools.propose_patch:propose_patch")
register("preview_diff", "repo_guardian_mcp.tools.preview_diff:preview_diff")
register("stage_patch", "repo_guardian_mcp.tools.stage_patch:stage_patch")

# sandbox session workflow
register("create_task_session", "repo_guardian_mcp.tools.create_task_session:create_task_session")
register("get_session_workspace", "repo_guardian_mcp.tools.get_session_workspace:get_session_workspace")
register("get_session_status", "repo_guardian_mcp.tools.get_session_status:get_session_status")
register("preview_session_diff", "repo_guardian_mcp.tools.preview_session_diff:preview_session_diff")
register("structured_edit", "repo_guardian_mcp.tools.structured_edit:structured_edit")
register("apply_to_workspace", "repo_guardian_mcp.tools.apply_to_workspace:apply_to_workspace")
register("cleanup_sandbox", "repo_guardian_mcp.tools.cleanup_sandbox:cleanup_sandbox")
register("run_task_pipeline", "repo_guardian_mcp.tools.run_task_pipeline:run_task_pipeline")
register("run_validation_pipeline", "repo_guardian_mcp.tools.run_validation_pipeline:run_validation_pipeline")
register("rollback_session", "repo_guardian_mcp.tools.rollback_session:rollback_session")
