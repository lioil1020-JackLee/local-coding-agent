# Continue Setup

## 目前 Continue 的角色
Continue 不是這個專案的核心邏輯本體。
它比較像前端操作層。

真正負責安全修改的是：
- repo_guardian MCP server
- ConversationOrchestrator
- AgentPlanner
- EditExecutionOrchestrator
- sandbox / diff / validation / rollback

所以 Continue 的工作是：
- 接收使用者白話需求
- 把需求導向正確的 MCP workflow
- 不要自己亂改檔
- 不要直接退回內建編輯器當主線

## 目前正式建議的模型分工
### qwen25-main
負責：
- 聊天
- 分析
- 規劃
- 找入口點
- 解釋 repo
- 選擇適合的 workflow

### qwen25-builder
負責：
- 修改
- 執行安全編輯流程
- 整理 diff
- 整理 validation 結果

## 目前正式建議的 Continue 行為
### 分析任務
優先：
1. `repo_guardian_preview_user_request_plan_tool`
2. `repo_guardian_handle_user_request_tool`

### 修改任務
優先：
1. `repo_guardian_preview_user_request_plan_tool`
2. `repo_guardian_create_task_session_tool`
3. `repo_guardian_edit_file_tool`
4. `repo_guardian_preview_session_diff_tool`
5. `repo_guardian_run_validation_pipeline_tool`

必要時：
6. `repo_guardian_rollback_session_tool`

## 重要原則
- 分析任務不能改檔
- 修改任務不能把聊天文字寫進程式
- 高階工具優先，但修改主線目前以 session workflow 為主
- 不要把 Continue 內建編輯能力當主入口

## 目前已知狀態
### 已可運作
- 分析專案
- 修改 README 等單檔內容
- 預覽 diff
- 執行 validation
- rollback session

### 尚未完全收斂
- 更穩定的 retry 行為
- 更少重複 append
- 更少多餘對話
- 更像 Cursor 的回覆節奏

## 新對話接手時的提醒
如果 Continue 表現和預期不同，不要第一時間懷疑整個架構壞掉。
先分辨問題是：
1. Continue config routing 問題
2. MCP tool contract 問題
3. session / sandbox 問題
4. validation / diff contract 問題
