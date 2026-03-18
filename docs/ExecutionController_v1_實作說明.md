# ExecutionController v1 實作說明

## 這份文件的目的
這份文件不只是描述 `ExecutionController` class 本身，還要說明它在整個專案中的**現階段定位**：

> 它不是最終版 agent controller，  
> 而是讓專案能安全從 pipeline/backend 階段，逐步過渡到 **本地端 CLI Agent（具備 Skill）** 的關鍵相容邊界。

---

## 為什麼這份文件現在更重要
現在專案目標已明確升級為：

- 本地端 CLI agent
- skill-enabled
- 對標 Cursor Agent

在這個前提下，很多人可能會直覺想把 `ExecutionController` 重寫成「更像最終 agent runtime」的樣子。  
**目前不應該這樣做。**

因為真實情況是：
- 現有 safe-edit pipeline 還在穩定運作
- 舊 orchestrator / pipeline 仍被測試與主流程依賴
- 新舊兩代 execution contract 仍同時存在
- controller 現在負責的是「保住現有主線，並替未來 agent 化鋪路」

---

## 它目前真正的角色

### 1. 相容邊界
同時支援：
- 新版 handler-based controller 使用方式
- 舊版 `ExecutionRequest / ExecutionPlan / ExecutionStatus`
- `EditExecutionOrchestrator` 的 step-style 用法
- 舊欄位與舊初始化模式

### 2. 過渡性 runtime 中心
雖然還不是最終 planner / executor 架構，但目前它已經開始承接：
- retry
- fallback
- trace
- state/context 管理

這使它成為未來 agent runtime 演進的橋梁。

### 3. CLI agent 化的過渡支點
未來若要進入完整 CLI agent loop：
- plan
- execute
- validate
- recover
- select skill

那 `ExecutionController` 很可能會是中間的重要承接層。  
但在那之前，它必須先穩定扮演 compatibility boundary。

---

## 這一版不是什麼
現在這版 controller：

- 不是最終純化版 architecture
- 不是完整 planner-driven agent runtime
- 不是 skill router
- 不是代表 orchestrator 已被淘汰
- 不是可以任意刪除 legacy contract 的訊號

它目前是**為了保住 working baseline 並支撐未來 CLI agent 演進**而存在。

---

## 對未來修改者的建議
如果未來要把系統真正升級到更完整的 CLI agent + skill system：

### 正確順序
1. 先確認相容層與現有測試全部穩定
2. 在上層新增 planner / skill selection / execution graph
3. 漸進式收斂舊 contract
4. 最後才重構 controller 核心

### 不正確順序
- 直接把 controller 重寫成理想化 agent runtime
- 先刪 legacy API，再補相容
- 把 orchestrator 還活著這件事當成技術債直接消滅

---

## 目前穩定基準
本輪合作結束時，使用者本地測試結果為：

- `uv run pytest`
- **28 passed in 15.82s**

這是目前 controller 相容層的已知穩定基準。

---

## 最後一句提醒
如果你是未來的新助理，請先記住：

> **ExecutionController 現在最重要的任務，不是看起來多漂亮，而是穩定承接新舊 execution contract，讓整個專案能逐步走向完整的本地端 CLI Agent + Skill 系統。**
