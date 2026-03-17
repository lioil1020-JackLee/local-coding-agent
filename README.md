## 目前開發狀態（2026-03）

本專案目前正從「單一大型 pipeline 工具架構」轉換為「多工具 session 架構」，
以提升與 Continue MCP Agent 的相容性與穩定度。

### 舊架構

原本的設計主要依賴一個工具：

repo_guardian_run_task_pipeline_tool

這個工具會在一次呼叫中完成：

1. 建立 sandbox session
2. 建立 git worktree
3. 套用檔案修改
4. 產生 diff
5. 執行 validation
6. 更新 session metadata

在直接 Python 執行與 pytest 測試時運作正常，
但在 Continue MCP 工具呼叫時經常出現 **約 60 秒 timeout**。

觀察到的現象：

- MCP tool call 約 60 秒會 timeout
- Python 實際上已經執行完成
- Continue 先中止工具回傳

### 新架構（進行中）

目前正在改為以下較小型的 MCP 工具：

create_task_session_tool  
edit_file_tool  
preview_session_diff_tool  
run_validation_pipeline_tool  
rollback_session_tool  

這樣的設計可以：

- 每個 tool 執行時間保持在幾秒內
- 避免 Continue MCP 的 timeout
- 讓 Agent workflow 更容易控制

### 目前完成狀態

✔ pytest 全部通過  
✔ session 建立功能正常  
✔ sandbox 編輯服務正常  
✔ diff preview 功能正常  
✔ validation service 正常  

⚠ sandbox workspace 初始化仍需進一步改善

### 建議 Agent 工作流程

未來 Agent 建議依序呼叫：

1. create_task_session_tool
2. edit_file_tool
3. preview_session_diff_tool
4. run_validation_pipeline_tool
5. rollback_session_tool








