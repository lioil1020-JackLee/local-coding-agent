# ExecutionController v1 實作說明

## 這份文件的目的
這份文件不是只描述 class 長怎樣，而是要讓未來的新對話快速理解：
- 為什麼 `ExecutionController` 會長成現在這樣
- 為什麼它看起來像同時服務兩代設計
- 哪些地方不能隨便「整理乾淨」
- 它在整個 local-coding-agent 專案裡目前扮演什麼角色

## 背景
這個專案原本先有穩定的 safe edit pipeline，包含：
- session sandbox
- diff
- validation
- rollback
- task/session status

之後開始往更明確的 controller-based 架構前進，目標是把系統從「一組 MCP tools + 流程膠水」提升成更可擴充的 agent backend。

因此 `ExecutionController` 本來是下一階段設計的核心之一。

但真實情況是：當 controller 開始引入後，舊的 orchestrator / pipeline code 並沒有一次性消失，而是還繼續存在並被測試保護。結果就是 repo 裡同時存在：
- 新版 controller-style 測試與抽象
- 舊版 pipeline-style 測試與整合代碼

## 這次對話真正完成了什麼
在這輪合作中，`ExecutionController` 沒有被簡單重寫成「新架構專用版」，而是被做成 **相容層**。

最後穩定下來的版本，同時支援：
- 新版 handler-based controller 使用方式
- 舊版 `ExecutionRequest / ExecutionPlan / ExecutionStatus`
- `EditExecutionOrchestrator` 的 step-style 用法
- 舊欄位名稱與舊初始化方式，例如 `ExecutionStep(action=..., retry_limit=...)`

## 為什麼一定要做相容層
因為真實依賴面不只一個。

在這個 repo 裡，以下幾組東西共同決定 controller 不能隨便改：
- `tests/test_execution_controller.py`
- `tests/test_execution_controller_v1.py`
- `repo_guardian_mcp/services/edit_execution_orchestrator.py`
- `repo_guardian_mcp/services/task_orchestrator.py`
- `repo_guardian_mcp/tools/run_task_pipeline.py`

如果只看單一檔案，很容易誤判 controller 可以只為新的設計服務。實際上不是，因為舊鍊路還活著，而且使用者本地會直接跑完整 pytest 作為真相來源。

## 目前 controller 的角色
目前 `ExecutionController` 的角色不是「最後版 agent controller」，而是：

### 1. 穩定邊界
它把不同世代的 execution contract 包在一起，避免專案其他地方因為局部演進而互相撞壞。

### 2. 漸進式遷移支點
它允許專案在不破壞 safe-edit pipeline 的前提下，慢慢往更模組化的 planner/controller 架構移動。

### 3. 測試保護點
它目前被多組測試共同約束，因此是高風險變更點。

## 這一版的能力摘要
目前穩定版 controller 至少有以下特性：
- 可支援 handler registry 的新式執行
- 可支援舊式 request/plan flow
- 支援 retry / fallback 的基本控制
- 支援 trace/state 更新
- 支援 mapping-like context/state 讀取行為
- 支援新舊 `ExecutionStep` 欄位
- 支援較寬鬆的失敗種類列舉，例如 `FailureKind.TRANSIENT`、`FailureKind.TOOLING`

## 這一版不是什麼
未來新對話的助理要注意，現在這版 controller：
- 不是最終純化版架構
- 不是 planner/executor fully separated 完成版
- 不是代表 orchestrator 已完全淘汰
- 不是代表可以刪掉舊接口

它目前是「為了讓整個專案穩定演進」而存在的 compatibility boundary。

## 使用與修改建議
若未來要修改 `ExecutionController`：

### 先做的事
先閱讀：
- `tests/test_execution_controller.py`
- `tests/test_execution_controller_v1.py`
- `repo_guardian_mcp/services/edit_execution_orchestrator.py`
- `repo_guardian_mcp/services/task_orchestrator.py`
- `repo_guardian_mcp/tools/run_task_pipeline.py`

### 再做的事
先用小範圍測試確認，再跑完整 pytest。

### 不要做的事
不要因為看到某些欄位像 legacy 就直接刪掉；那通常代表某個舊鍊路還在依賴。

## 目前已知穩定狀態
本輪合作結束時，使用者本地測試結果為：
- `uv run pytest`
- **28 passed in 15.82s**

這是目前 `ExecutionController` 相容層的已知穩定基準。

## 建議下一步
下一步不是立刻再大改 controller，而是：
1. 先把 session lifecycle 更完整接到 orchestration entry points
2. 再思考 planner + executor 的正式升級
3. 等這兩件事穩後，再考慮收斂 legacy 接口

## 對未來新對話的提醒
如果你是未來的新助理，讀到這裡時請先記住：
- 不要把 controller 當成可以直接重寫的獨立模組
- 它目前是多條 execution 路徑的共用穩定層
- 先守住測試與 working baseline，再談優化
