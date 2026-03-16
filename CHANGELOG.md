## 2026-03-17

### MCP 工具架構重大調整

repo_guardian MCP 工具架構由「單一 pipeline 工具」改為「多工具架構」。

#### 舊設計

單一工具：

run_task_pipeline_tool

此工具會同時執行：

- session 建立
- sandbox 建立
- 檔案修改
- diff 產生
- validation
- session metadata 更新

在 Continue MCP 環境中可能觸發 tool timeout。

#### 新設計

改為以下工具：

create_task_session_tool  
edit_file_tool  
preview_session_diff_tool  
run_validation_pipeline_tool  
rollback_session_tool  

優點：

- 避免 MCP tool timeout
- Agent workflow 更清楚
- 每個工具責任單一

#### 測試狀態

目前測試全部通過：

pytest → 14 passed

測試涵蓋：

- analysis tools
- session status
- repo overview
- rollback
- run_task_pipeline
- validation service