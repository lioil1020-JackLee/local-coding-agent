# Tool Contracts

本文件描述 MCP tools 的輸入與輸出結構。

Tool contract 的目的：

-   讓 agent 可以穩定呼叫 tools
-   保持 API 結構一致
-   方便未來擴充

------------------------------------------------------------------------

# run_task_pipeline

主要 editing tool。

## Input

repo_root: str

單一操作：

relative_path: str mode: "append" \| "replace" content: str old_text:
str (replace mode)

或多操作：

operations: list

Example:

{ "relative_path": "README.md", "mode": "append", "content": "hello" }

------------------------------------------------------------------------

## Output

{ "ok": true, "session_id": "...", "edited_files": \[...\], "diff_text":
"...", "changed": true, "summary": "..." }

------------------------------------------------------------------------

# get_session_status

取得 session 狀態。

## Input

session_id: str

------------------------------------------------------------------------

## Output

{ "ok": true, "session_id": "...", "status": "validated", "changed":
true, "edited_files": \[...\], "validation": {...} }

------------------------------------------------------------------------

# preview_session_diff

查看 sandbox diff。

## Input

session_id: str

------------------------------------------------------------------------

## Output

{ "ok": true, "diff": "..." }

------------------------------------------------------------------------

# create_task_session

建立 sandbox session。

## Output

{ "session_id": "...", "sandbox_path": "...", "branch_name": "..." }

------------------------------------------------------------------------

# Design Rules

所有 tool response 都應包含：

ok error (optional)

這樣 agent 可以安全判斷是否成功。
