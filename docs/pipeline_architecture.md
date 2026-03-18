# Pipeline Architecture

## 這份文件存在的原因
這份文件要幫未來的新對話理解一件很重要的事：

> 目前專案雖然已經有 working safe-edit pipeline，  
> 但它的終極方向已不只是 pipeline，而是要演進成 **本地端 CLI Agent（具備 Skill 系統）**。

因此，現在的 pipeline 應被理解為：
- 已可用的穩定主線
- 未來 agent runtime 的基礎骨架
- 不是最終終點

---

## 目前架構的正確理解
目前系統可被理解為「穩定可用，但仍在演進中的分層架構」。

### 已穩定存在的部分
- sandbox/session-based edit workflow
- diff generation
- validation pipeline
- rollback support
- session status management
- `run_task_pipeline` wrapper entry point
- `ExecutionController` 相容層
- session lifecycle phase 1

### 正在往前演進的方向
- planner / executor 分層
- 更明確的 agent loop
- skill abstraction
- CLI product surface
- Continue / IDE integration
- 更完整的 session lifecycle 管理

---

## 從 pipeline 到 CLI agent 的演進觀點
目前主線可以簡化理解為：

1. 接收請求
2. 標準化任務輸入
3. 建立或使用 session sandbox
4. 在 sandbox 執行修改
5. 預覽 diff
6. 跑 validation
7. 必要時 rollback
8. 回傳狀態與結果

這條路徑已經是 working baseline。  
未來要做的不是推翻它，而是**在它之上逐步補上更完整的 agent 能力**，例如：

- planning
- multi-step execution
- retry / fallback policy
- skill selection
- richer trace / memory
- 更好的 CLI 互動體驗

---

## 目前各模組的定位

### `run_task_pipeline`
目前仍是重要的使用者入口與測試入口。  
未來即使加入更完整 agent 規劃，這層仍可能保留作為 CLI 或 tool 的穩定 facade。

### `EditExecutionOrchestrator`
表達 safe-edit pipeline 的核心意圖，是現有修改主線的重要組織點。

### `ExecutionController`
目前是 execution compatibility boundary。  
未來可能成為更完整 agent runtime 的中層控制節點，但現在不能把它誤當最終結構。

---

## Session model 為什麼仍然是核心
若專案最終要成為可靠的本地端 CLI agent，session / sandbox 模型仍然非常重要，因為它直接支撐：

- 安全修改
- 可回溯
- rollback
- validation isolation
- 多次任務之間的狀態管理
- 長期 CLI 使用時的 lifecycle control

---

## 為什麼 skill system 會接在這上面
未來的 skill system 並不是與 pipeline 無關的新東西。  
更合理的理解是：

- 現在的 tools / pipeline steps  
  ⟶ 未來可被抽象為 skills / execution graph nodes

例如：
- refactor skill
- validation skill
- rollback skill
- repo analysis skill
- docs update skill

這樣專案才會從「能改檔的安全流程」真正升級成「具備 skill 的 CLI agent」。

---

## 未來最合理的架構收斂方向
1. 保持 safe-edit pipeline 綠燈
2. 集中 session lifecycle logic
3. 在 controller 之上加入 planner / executor
4. 引入 skill abstraction
5. 強化 CLI UX
6. 再做 Continue 深整合

---

## 一句話總結
> **現在的 pipeline 不是過時設計，而是 local-coding-agent 走向本地端 CLI Agent + Skill 系統的現役基礎主線。**
