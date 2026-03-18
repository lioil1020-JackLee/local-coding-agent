# CONTRIBUTING 開發指南

## 這份文件的目的
這份文件不只記錄開發慣例，也要幫未來參與者理解：  
**這個專案現在的終極目標已經不是單純維護 safe-edit backend，而是逐步建成一個本地端 CLI Agent（具備 Skill 系統），並對標 Cursor Agent。**

因此，所有貢獻都應同時顧及兩件事：

1. **保護目前 working baseline**
2. **讓架構逐步朝完整 CLI agent / skill system 演進**

---

## 專案哲學

### 1. Safe-by-default
- 所有修改都應在 sandbox/session 中發生
- diff / validation / rollback 不是附加功能
- session metadata 是 lifecycle 與 recovery 的單一真實來源

### 2. Agent-first
- 不把系統視為單純工具集合
- 最終目標是 planner / executor / validator / recovery loop
- 現有 controller / orchestrator 是通往 agent runtime 的過渡主線

### 3. CLI-first
- CLI 是產品主介面之一，不只是 debug 入口
- 設計應考慮 interactive 與 scriptable 兩種使用情境

### 4. Skill-enabled
- 新能力應盡量朝可模組化、可重用、可組合的 skill 方向設計
- 未來 tools 與 pipeline 會逐步被 skill abstraction 包裝與提升

---

## 現況提醒
目前 repo 同時存在：
- 舊的 pipeline / orchestrator 流程
- 新的 controller-style 抽象
- 已落地的 session lifecycle phase 1
- 穩定的 safe-edit pipeline

不要假設任何一層已經完全淘汰另一層。

尤其 `ExecutionController` 目前是**相容層**，不是可以隨便純化重寫的最終架構。

---

## 高風險修改前的必要檢查
若要改以下檔案，請先整體閱讀再動手：

- `repo_guardian_mcp/services/execution_controller.py`
- `repo_guardian_mcp/services/edit_execution_orchestrator.py`
- `repo_guardian_mcp/services/task_orchestrator.py`
- `repo_guardian_mcp/tools/run_task_pipeline.py`
- `tests/test_execution_controller.py`
- `tests/test_execution_controller_v1.py`
- `tests/test_run_task_pipeline.py`
- `tests/test_validation_pipeline.py`
- `tests/test_rollback_session.py`

因為這些檔案共同定義了 execution contract。

---

## 貢獻時應多問自己 4 個問題

1. 這個改動有沒有保護 safe-edit pipeline？
2. 這個改動是讓系統更接近 CLI agent 嗎？
3. 這個改動未來能 skill 化嗎？
4. 這個改動有沒有破壞相容層或 working baseline？

---

## 文件更新要求
文件不能只寫簡短摘要。  
這個專案的 docs 也是跨對話 handoff 系統的一部分，應盡量回答：

- 目前做到哪裡
- 現在的定位是什麼
- 哪些設計是相容邊界
- 為什麼不能亂改
- 下一步如何往 CLI agent + skill system 前進

---

## 測試要求
目前已知穩定基準：

- `uv run pytest`
- **28 passed**

任何重要架構修改，應盡量保住這個基準，或清楚說明為何要改變測試契約。

---

## 現在最值得的貢獻方向
1. skill abstraction / skill registry
2. planner + executor agent loop
3. CLI UX / 命令入口
4. session lifecycle deeper integration
5. Continue / IDE integration（在 backend 穩定後）
