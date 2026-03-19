# ExecutionController 說明

## 這份文件的定位

`ExecutionController` 是本專案中最容易被誤解、也最容易被過度重構的部分之一。  
這份文件的目的是要明確說明它在現階段的責任與定位。

> **它目前不是最終形態的 agent runtime，**
> **而是從既有 pipeline / orchestrator 世界，走向完整 CLI agent 的核心過渡邊界。**

---

## 為什麼它很重要

當專案還只是工具集合時，controller 容易被當成「包一下 orchestration 的類別」。  
但在本專案目前的演進狀態下，`ExecutionController` 已經承擔更重要的意義：

- 新舊 execution 契約的兼容點
- 上層 agent loop 的控制節點
- trace / state / retry 思維的承接點
- skill execution 流程的過渡入口

---

## 現在不應怎麼看它

目前不應把 `ExecutionController` 誤認為：

- 已經完成的最終 controller 架構
- 可隨意刪除舊契約的證據
- 足以代表整個 agent runtime 的全部
- 已完全取代 pipeline / orchestrator 的單一真相來源

如果這樣理解，後續很容易破壞 working baseline。

---

## 現在應怎麼看它

比較正確的理解是：

### 1. Compatibility Boundary
它承接了不同時期的 execution model 與使用方式。  
這讓現有測試與主流程得以持續運作。

### 2. Agent Control Pivot
現在新增的 CLI agent flow 已經開始利用 controller 思維來表達：

- `preview_plan`
- `select_skill`
- `execute_skill`
- `validate_skill`
- `finalize`

這說明 controller 已經開始成為 agent runtime 的控制樞紐之一。

### 3. Future Expansion Anchor
未來若要增加：
- richer retry
- fallback policy
- multi-step execution trace
- confirmation checkpoints
- human-in-the-loop decisions

最合理的承接點之一仍然會是 controller。

---

## 目前可觀察到的 agent loop 雛形

從目前 CLI 執行結果來看，已經出現相對清楚的 execution steps：

1. `preview_plan`
2. `select_skill`
3. `execute_skill`
4. `validate_skill`
5. `finalize`

這代表專案已經從單純的 function call / pipeline entry，進入高階任務流程控制的第一步。

但要注意：

### 這還不是完整 agent loop
目前仍缺少：
- 更細的 retry policy
- failure classification
- fallback skill selection
- interactive confirmation
- richer plan decomposition
- memory / history integration

---

## 與 skill system 的關係

### controller 不等於 skill system
skill system 負責的是高階能力模組化。

### controller 不等於 pipeline
pipeline 負責底層安全執行。

### controller 的位置
controller 比較像是夾在兩者中間的「控制與銜接層」：

- 從 CLI / agent runtime 接收高層任務
- 協調 skill 與 execution steps
- 把工作交給底層 pipeline / services
- 收斂 trace 與結果

---

## 為什麼現在不能直接大重寫

目前專案本地測試已達：

- `35 passed`

這代表現有 controller 所承擔的兼容責任是真實存在的。  
如果直接用理想化方式重寫 controller，很容易導致：

- 舊測試失敗
- `run_task_pipeline` 契約破壞
- CLI 或 agent service 接線不穩
- execution trace 失真
- session / validation 行為出現回歸

因此，**controller 目前最重要的任務不是漂亮，而是穩。**

---

## 未來正確的演進順序

### 第一階段：維持相容穩定
- 不破壞既有測試
- 不破壞現有 CLI 功能
- 不破壞 safe-edit pipeline

### 第二階段：在上層加能力
- richer plan model
- fallback policy
- better skill routing
- execution metadata

### 第三階段：再收斂 controller 內部
當 skill system 與 CLI 已穩定後，再來做 controller 純化，會安全得多。

---

## 對未來修改者的提醒

若你要修改 `ExecutionController`，請先問自己：

1. 這個改動是讓 CLI agent 更強，還是只是讓程式看起來更漂亮？
2. 這會不會破壞既有 execution contract？
3. 這會不會讓 skill flow 與 pipeline flow 斷掉？
4. 這是否仍維持 safe-by-default？

---

## 一句話總結

> **ExecutionController 現在最重要的價值，不是成為最終 architecture，而是穩定承接既有 execution contract，同時讓 CLI agent 與 skill system 能往上長。**
