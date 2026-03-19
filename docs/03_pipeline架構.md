# Pipeline 架構

## 這份文件的目的

這份文件要說明一件很重要的事：

> 本專案現在雖然已經有可運作的 pipeline，
> 但 pipeline 不是終點，而是走向完整 CLI agent 的現役主線。

如果沒有這個理解，很容易犯兩種錯：

1. 把 pipeline 當成過時設計想全部推翻
2. 把 pipeline 當成最終設計，忽略 skill 與 agent runtime 的上層演進

這兩種都不對。

---

## 現在的 pipeline 承擔什麼角色

目前 pipeline 架構主要負責：

- 建立執行上下文
- 進入 sandbox / session
- 執行修改
- 產生 diff
- 跑 validation
- 回傳結果
- 必要時執行 rollback
- 提供狀態查詢與後續恢復能力

換句話說，pipeline 目前承擔的是「可靠、安全、可測試」的執行主線。

---

## 為什麼 pipeline 還是非常重要

因為不論未來 agent 有多高階，底下仍然需要一條穩定路徑來真正修改程式碼。

也就是說：

- planner 可以規劃
- skill 可以決定做什麼
- CLI 可以讓使用者下命令

但真正把事情安全做完的，仍然需要穩定的 pipeline / orchestrator / service 結構。

---

## 現在的主流程如何理解

目前可以把 execution flow 概念化為：

1. 接收任務輸入
2. 正規化成內部請求格式
3. 準備或建立 session
4. 在 sandbox 中執行修改或分析
5. 產生結果與必要 diff
6. 執行 validation
7. 成功則 finalize，失敗則回報或 rollback
8. 保存狀態供查詢與恢復

對於 analyze 類 skill，可能不需要 session。  
對於 safe-edit 類 skill，就會更完整走進 session / validation / rollback 路徑。

---

## pipeline 與 agent loop 的關係

### 不正確理解
- pipeline = 舊設計
- agent loop = 新設計
- 所以直接刪掉 pipeline

### 正確理解
- pipeline = 穩定底層執行主線
- agent loop = 更高層的任務控制與 skill 編排
- skill = 把高階能力模組化後，接到 pipeline 或 service 能力上

因此真正合理的架構是：

```text
CLI
  -> Agent Runtime
      -> Skill
          -> Pipeline / Orchestrator
              -> Services
                  -> Session / Sandbox
```

---

## 目前值得注意的實作層次

### 1. `run_task_pipeline`
目前仍是很重要的穩定入口。  
即使未來 CLI 更完整，這層仍可能作為：

- facade
- backward compatibility entry
- 測試穩定點

### 2. `EditExecutionOrchestrator`
負責安全修改工作流的重要組織點。  
它不只是內部工具，而是 safe-edit runtime 的主要骨架之一。

### 3. `ExecutionController`
目前扮演控制邊界與過渡主線角色。  
它不應被誤認為完全取代所有 orchestrator，但它確實是更高層控制能力的承接點。

---

## pipeline 與 skill system 如何銜接

skill system 不是要取代 pipeline，而是要把「做什麼」與「怎麼安全做」分開。

### skill 關心的事情
- 這個任務屬於什麼能力
- 需要哪些步驟
- 要不要 session
- 要不要 validation
- 如何驗證結果成功

### pipeline 關心的事情
- 如何在既有系統裡安全執行
- 如何產生 diff / validation / rollback
- 如何維持 session consistency

所以合理分工應該是：

- skill：高層意圖與流程抽象
- pipeline：底層安全執行主線

---

## 目前 pipeline 架構的優勢

### 1. 已可運作
目前已有穩定測試基準，代表不是紙上設計。

### 2. 已有安全基礎
sandbox、validation、rollback 都在。

### 3. 已有 session 模型
這是往長期 agent 演進最重要的資產之一。

### 4. 已能與 CLI / controller 接線
代表上層產品面已開始長出來。

---

## 目前 pipeline 架構的限制

### 1. 高層語意還不夠清楚
目前雖然能執行，但還需要更明確的 plan / skill / agent 概念來組織任務。

### 2. 多步任務的抽象還不夠成熟
未來可能需要真正的 task graph 或 richer plan model。

### 3. 使用者體驗還偏工程向
CLI 目前可用，但還不是完整產品體驗。

---

## 下一步最合理的演進方式

1. 不破壞現有 pipeline 測試綠燈
2. 在上層逐步擴充 skill system
3. 讓 CLI 呼叫 skill 而不是直接面向底層細節
4. 讓 controller 更像高階 agent runtime，而不是單純轉接層
5. 補 richer trace / confirmation / fallback

---

## 一句話總結

> **目前的 pipeline 不是舊包袱，而是 local-coding-agent 往完整本地端 CLI agent 演進時，最重要的安全執行底座。**
