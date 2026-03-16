## 開發說明（MCP Tools）

本專案主要提供 Continue MCP Agent 使用。

### 重要設計原則

避免設計「大型 mega tool」。

建議使用多個小工具組合：

GOOD：

create_session → edit_file → preview_diff → validate → rollback

BAD：

run_everything_pipeline

大型工具容易超過 MCP timeout。

### 本地測試

執行：

uv run pytest

預期結果：

14 passed

### MCP Server

啟動：

python -m repo_guardian_mcp.server

Runtime 目錄：

agent_runtime/

包含：

sessions/  
sandbox_worktrees/  
mcp_debug.log  
git_debug.log