# ExecutionController v1 實作說明

本包提供的是 **ExecutionController v1 程式碼骨架**，目的不是直接取代你現有 repo 的所有 orchestrator，
而是幫你建立一個正式的「流程控制中心」。

## 內含檔案

1. `repo_guardian_mcp/services/execution_controller.py`
   - 提供統一資料模型：
     - `ExecutionRequest`
     - `ExecutionPlan`
     - `ExecutionStep`
     - `ExecutionContext`
     - `StepResult`
     - `ExecutionResult`
   - 提供 `ExecutionController` 類別
   - 內建 v1 保守版 retry / stop / rollback 規則

2. `tests/test_execution_controller_v1.py`
   - 提供可直接理解的測試骨架
   - 驗證：
     - 正常主線成功
     - create_session 失敗一次後重試成功
     - edit 失敗直接 stop
     - validate 失敗觸發 rollback
     - analyze 任務不建立 session

## v1 規則摘要

### 修改任務主線
`preview_plan -> create_session -> edit -> preview_diff -> validate -> rollback(必要時)`

### 分析任務主線
`preview_plan -> analyze`

### retry 規則
- `create_session`：允許 retry 1 次
- 其他步驟：預設不 retry

### rollback 規則
- `validate` 失敗且已有 session：直接 rollback
- 明確標記 `rollback_on_failure=True` 的步驟：允許 rollback

### 明確禁止
- edit 失敗後自動改用別的編輯方式
- validation 失敗後自動再 patch 一次
- 分析任務偷偷改檔

## 建議接線順序

1. 先把 `execution_controller.py` 放進 `repo_guardian_mcp/services/`
2. 先不要刪除既有 `task_orchestrator.py` / `edit_execution_orchestrator.py`
3. 先讓它們改成被 `ExecutionController` 呼叫
4. 補現有 `tests/test_execution_controller.py`
5. 再慢慢把 MCP tools 入口改成呼叫 `ExecutionController`

## 重要提醒

這個骨架是「安全保守版」，目的是先讓控制層正式成形。
它不是最終版，也不假設你現在的所有 service 介面與此完全一致。

因此你在合併時，應優先確認：

- 現有 `session_service` 的方法名稱
- 現有 `edit_execution_orchestrator` 的 edit / diff 呼叫方式
- 現有 `validation_service` 與 `rollback_service` 的回傳格式
- 現有 `task_orchestrator` 是否要保留當 adapter

## 建議測試流程

1. 先覆蓋檔案
2. 跑：
   - `uv run pytest -q`
3. 若失敗，優先對齊 service 介面
4. 修正後再次執行測試
