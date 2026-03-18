# local-coding-agent（更新版）

## 🧠 Execution Pipeline（已穩定）

核心流程：

TaskOrchestrator
→ EditExecutionOrchestrator
→ ExecutionController
→ Steps:
    - create_session
    - load_session
    - apply_edit
    - preview_diff
    - validation
    - persist_session

### 特點
- session-based sandbox（copy-based）
- retry / fallback / trace 支援
- validation / rollback 已串通

---

## 🔄 run_task_pipeline

目前為 wrapper：
- 對外簡化 API
- 實際邏輯在 EditExecutionOrchestrator

---

## 📦 Session Workflow

1. create session
2. edit sandbox
3. diff
4. validation
5. persist

狀態：
- pending
- validated
- validation_failed
- no_change

---

## 🧪 測試

23 passed
