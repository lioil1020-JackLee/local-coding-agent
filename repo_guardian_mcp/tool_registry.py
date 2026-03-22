from __future__ import annotations

from importlib import import_module
from typing import Callable

TOOLS: dict[str, str] = {}


def register(name: str, target: str) -> None:
    TOOLS[name] = target


def register_with_repo_guardian_alias(name: str, target: str) -> None:
    """同時註冊短名稱與 Continue 相容名稱。"""
    register(name, target)
    if not name.startswith("repo_guardian_"):
        register(f"repo_guardian_{name}_tool", target)


def get_tool(name: str) -> Callable:
    if name not in TOOLS:
        raise KeyError(f"Tool not found: {name}")
    module_path, func_name = TOOLS[name].split(":")
    module = import_module(module_path)
    return getattr(module, func_name)


def list_tools() -> list[str]:
    return sorted(TOOLS.keys())


register_with_repo_guardian_alias("analyze_repo", "repo_guardian_mcp.tools.analyze_repo:analyze_repo")
register_with_repo_guardian_alias("find_entrypoints", "repo_guardian_mcp.tools.find_entrypoints:find_entrypoints")
register_with_repo_guardian_alias("get_session_status", "repo_guardian_mcp.tools.get_session_status:get_session_status")

register_with_repo_guardian_alias("create_task_session", "repo_guardian_mcp.tools.create_task_session:create_task_session")
register_with_repo_guardian_alias("preview_session_diff", "repo_guardian_mcp.tools.preview_session_diff:preview_session_diff")
register_with_repo_guardian_alias("run_validation_pipeline", "repo_guardian_mcp.tools.run_validation_pipeline:run_validation_pipeline")
register_with_repo_guardian_alias("rollback_session", "repo_guardian_mcp.tools.rollback_session:rollback_session")
register_with_repo_guardian_alias("run_task_pipeline", "repo_guardian_mcp.tools.run_task_pipeline:run_task_pipeline")

register_with_repo_guardian_alias("search_codebase", "repo_guardian_mcp.tools.search_code:search_code")
register_with_repo_guardian_alias("get_code_region", "repo_guardian_mcp.tools.read_code_region:read_code_region")
register_with_repo_guardian_alias("get_repo_overview", "repo_guardian_mcp.tools.repo_overview:repo_overview")

register_with_repo_guardian_alias("propose_patch", "repo_guardian_mcp.tools.propose_patch:propose_patch")
register_with_repo_guardian_alias("preview_diff", "repo_guardian_mcp.tools.preview_diff:preview_diff")
register_with_repo_guardian_alias("stage_patch", "repo_guardian_mcp.tools.stage_patch:stage_patch")

register_with_repo_guardian_alias("move_file", "repo_guardian_mcp.tools.move_file:move_file")
register_with_repo_guardian_alias("cleanup_sandbox", "repo_guardian_mcp.tools.cleanup_sandbox:cleanup_sandbox")
register_with_repo_guardian_alias("cleanup_sessions", "repo_guardian_mcp.tools.cleanup_sessions:cleanup_sessions_tool")
register_with_repo_guardian_alias("list_sessions", "repo_guardian_mcp.tools.list_sessions:list_sessions_tool")
register_with_repo_guardian_alias("pin_session", "repo_guardian_mcp.tools.pin_session:pin_session_tool")
register_with_repo_guardian_alias("resume_session", "repo_guardian_mcp.tools.resume_session:resume_session_tool")

# Continue / 高階工作流入口
register_with_repo_guardian_alias("preview_user_request_plan", "repo_guardian_mcp.tools.workflow_gateway:preview_user_request_plan")
register_with_repo_guardian_alias("handle_user_request", "repo_guardian_mcp.tools.workflow_gateway:handle_user_request")
register_with_repo_guardian_alias("edit_file", "repo_guardian_mcp.tools.workflow_gateway:edit_file")
