# Workflow

## 目前正式採用的 workflow

### A. 分析任務（唯讀）
適用情況：
- 幫我分析這個專案
- 幫我看懂這個 repo
- 幫我找入口點
- 先不要改，先解釋

流程：
1. `preview_user_request_plan_tool`
2. `handle_user_request_tool`

原則：
- 不可修改檔案
- 結果只回在 chat
- 不可把分析內容寫進程式

### B. 修改任務（安全修改）
適用情況：
- 幫我修改 README
- 幫我新增一個函式
- 幫我修正某段邏輯

流程：
1. `preview_user_request_plan_tool`
2. `create_task_session_tool`
3. `edit_file_tool`
4. `preview_session_diff_tool`
5. `run_validation_pipeline_tool`
6. 必要時 `rollback_session_tool`

原則：
- 修改只發生在 sandbox
- 先看 diff，再驗證
- 失敗時必要可回滾

## 為什麼目前不用 handle_user_request_tool 當修改主線
因為實測已證明：
- 它很適合唯讀分析
- 但在修改任務上曾發生 timeout

所以目前正式策略是：
- 分析 → 高階 handle 主線
- 修改 → 高階 preview + 低階安全 session workflow

## 目前 workflow 的優點
- 比單一 mega tool 穩
- 比直接用 Continue 內建編輯安全
- 比 git worktree 主線更不容易 timeout
- 可讀、可 debug、可逐步擴充

## 目前 workflow 仍待補強的地方
- append 需要避免重複寫入
- 缺少 ExecutionController
- fallback policy 還可以更穩
- validation policy 還可以更細

## 接下來要升級成的 workflow（v2）
未來正式目標：

使用者說人話
→ ConversationOrchestrator
→ AgentPlanner
→ ExecutionController
→ ToolAdapter
→ Sandbox / Diff / Validation

也就是：
不是讓模型自己亂串工具，
而是讓系統正式掌控執行流程。
