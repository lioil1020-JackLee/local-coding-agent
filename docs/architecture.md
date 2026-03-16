# Architecture

本文件描述 **local-coding-agent / repo_guardian MCP server**
的整體架構。

系統設計目標：

-   安全修改 repository
-   每個任務隔離 sandbox
-   所有變更可追蹤
-   MCP tools 可供 agent 使用

------------------------------------------------------------------------

# High-Level Architecture

MCP Client ↓ MCP Server (FastMCP) ↓ Tool Layer ↓ Task Orchestrator ↓
Services ↓ Sandbox Git Worktree

------------------------------------------------------------------------

# Component Overview

## MCP Server

入口點：

repo_guardian_mcp/server.py

負責：

-   提供 MCP tool API
-   將 tool request 導向對應 function
-   管理 workspace root

Example tools:

run_task_pipeline get_session_status repo_overview search_codebase
preview_diff stage_patch

------------------------------------------------------------------------

# Tool Layer

位置：

repo_guardian_mcp/tools/

功能：

-   封裝 MCP tools
-   處理輸入參數
-   呼叫 services

Examples:

run_task_pipeline.py get_session_status.py create_task_session.py
preview_session_diff.py

------------------------------------------------------------------------

# Task Orchestrator

位置：

repo_guardian_mcp/services/task_orchestrator.py

負責：

-   組合多個 services
-   控制 coding pipeline

Pipeline:

create_task_session ↓ apply_text_edit / apply_text_operations ↓
preview_session_diff ↓ run_validation_hook ↓ update_session_file

------------------------------------------------------------------------

# Services Layer

位置：

repo_guardian_mcp/services/

負責核心邏輯。

主要 services：

sandbox_edit_service session_update_service validation_hook_service

------------------------------------------------------------------------

# Sandbox Environment

每個 session 都會建立：

agent_runtime/sandbox_worktrees/`<session_id>`{=html}

這是一個 git worktree。

好處：

-   不會污染主 workspace
-   每個任務完全隔離
-   diff 可追蹤

------------------------------------------------------------------------

# Session Metadata

每個任務會產生：

agent_runtime/sessions/`<session_id>`{=html}.json

Example fields:

session_id repo_root sandbox_path branch_name base_commit

status edited_files changed summary validation

------------------------------------------------------------------------

# Design Principles

Isolation Traceability Safe Editing Tool-first architecture

------------------------------------------------------------------------

# Future Architecture (v2)

Planner Agent Semantic Patch Generator Impact Analysis Engine Automated
Test Runner Patch Review Workflow
