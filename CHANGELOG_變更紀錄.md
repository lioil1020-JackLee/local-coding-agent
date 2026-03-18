# CHANGELOG

本文件記錄 local-coding-agent 專案的重要變更、架構決策與目前狀態修正。  
它的目的不是追求嚴格的 SemVer，而是讓未來維護者、未來的 AI 助理、以及使用者能快速理解：

- 過去做了哪些重要調整
- 為什麼要調整
- 哪些內容已經完成
- 哪些內容仍在進行中
- 哪些舊文件已經落後

---

## 2026-03-18：文件與真實狀態重新校正

這一輪不是單純補文字，而是根據：

- 目前 repo 結構
- 已存在的測試檔案
- 實際執行 `uv run pytest`
- 實際啟動 `python -m repo_guardian_mcp.server`
- 已上傳與既有設計文件
- Continue / config 設定現況

重新對文件做一次「實作狀態校正」。

### 本次確認的關鍵事實

#### 1. pytest 基準更新
先前部分文件仍記錄為：

- `14 passed`

但依最新實測，現況為：

- `18 passed`

這代表測試基準已向前推進，舊文件已落後。

#### 2. ExecutionController 狀態修正
舊文件曾描述：

- ExecutionController 尚未實作

但目前實際情況是：

- 已存在 `test_execution_controller.py`
- 且測試可通過

因此更準確的說法是：

- **ExecutionController 已有初步實作與測試覆蓋**
- 但尚未表示完整的 retry / stop / fallback / multi-turn agent 全部成熟

#### 3. session workflow 狀態修正
舊文件曾將專案描述為：

- 正在從大型 pipeline 工具架構過渡到多工具 session 架構

這個方向本身沒有錯，但目前更準確的狀態應為：

- **session workflow 已經是主線**
- 舊式單一大型工具流程已不再是建議主流程

#### 4. server 啟動形式修正
目前已確認：

- `python -m repo_guardian_mcp.server` 可啟動
- 啟動時沒有明顯輸出，符合 stdio 型 MCP server 的待命特徵

因此文件中若將目前 server 完整視為已成熟的 HTTP FastAPI 對外服務，需謹慎描述，避免誤導。

---

## 2026-03-17：MCP 工具架構重大調整

### 背景
最初的設計傾向使用一個較大的 pipeline 工具，一次完成多個步驟。  
這種做法在直接 Python 執行與部分測試場景中可用，但在 Continue / MCP tool call 場景下，容易遇到 timeout、回傳中斷與追蹤困難。

### 核心改動
由「單一大型 pipeline 工具」逐步改為「多工具、單一責任」架構。

#### 舊設計傾向
大型工具一次完成：
- 建立 session
- 建立 sandbox
- 套用檔案修改
- 產生 diff
- 執行 validation
- 更新 metadata

#### 新設計傾向
拆分為較小型工具，例如：
- `create_task_session_tool`
- `edit_file_tool`
- `preview_session_diff_tool`
- `run_validation_pipeline_tool`
- `rollback_session_tool`

### 這次調整的意義
1. 減少單次 tool call 責任範圍
2. 降低 Continue timeout 機率
3. 讓 Agent / Controller 更容易掌握狀態
4. 讓未來 retry / fallback 更容易定義
5. 讓工具更容易單元測試

---

## 2026-03：核心架構建立期

這個階段的重點不是功能數量，而是建立一套能持續演化的底座。

### 已建立的基礎能力
- MCP server (`repo_guardian_mcp`)
- Continue integration
- 安全修改 workflow
- session sandbox
- diff / validation / rollback pipeline
- 分析工具與 repo 掃描基礎能力
- patch proposal / diff / stage 類型工具雛形

### Safe Edit Workflow 正式確立
主線安全修改流程逐步被定義為：

1. preview plan
2. create session
3. edit sandbox / stage patch
4. preview diff
5. run validation
6. rollback（必要時）

這代表專案已明確把「安全流程」放在「直接改檔」之前。

---

## copy-based sandbox 成為主線的原因

先前曾嘗試採用 `git worktree` 方向。  
但實務上觀察到：

- Continue + MCP tool call 下較容易卡住或 timeout
- 建立與清理成本較高
- 除錯與狀態追蹤較複雜

因此目前主線轉向：

- **copy-based sandbox**

### 主要優點
- 建立速度更快
- 結構更單純
- 對本地 agent workflow 更直觀
- 更適合作為 session 隔離底座

---

## Continue integration 的實際意義

Continue 的整合目前不應只理解成「接得上 server」，而應理解成：

1. 可以透過 config 對模型與工具使用方式做出限制
2. 可以把分析模式與修改模式拆開
3. 可以把 session workflow 明確寫進 agent 行為規則
4. 可以降低模型在修改任務時亂跳流程的風險

### 目前已可做到的方向
- 分析 repo
- 尋找入口點
- 進行修改流程
- 預覽 diff
- 執行 validation
- rollback session

### 目前仍需持續收斂的方向
- 工具選擇策略
- timeout 風險管理
- 說明輸出的一致性
- 專案導覽模式與局部分析模式的界線

---

## 測試里程碑

### 舊記錄
- `14 passed`

### 目前最新基準
- `18 passed`

### 目前可確認已有測試涵蓋的方向
- analysis tools
- execution controller
- session status
- repo overview
- rollback
- run_task_pipeline
- text guard
- validation pipeline
- validation service

這代表目前的測試基準比早期文件描述更完整。

---

## 已知問題與仍待強化的方向

### 1. idempotent edit 仍需持續補強
舊問題沒有完全失效，仍值得保留：
- append 可能重複寫入
- 某些操作仍需更明確的 no-op / no-change 判斷

建議持續強化：
- `append_if_missing`
- `replace_once`
- no-change 狀態標記
- patch 套用前後一致性檢查

### 2. retry / stop / fallback 需要更完整規格
ExecutionController 雖已存在，但：
- 什麼情況該 retry
- 什麼情況該 stop
- 什麼情況能 fallback
- fallback 能跳去哪一層

仍需更清楚的策略文件與程式實作。

### 3. 對話記憶仍未達成熟狀態
雖已有 conversation / session 概念，但尚未成熟到：
- 長期記憶
- 多輪目標追蹤
- 跨輪補丁接續
- 中斷恢復

### 4. HTTP / FastAPI 產品化仍需釐清
設計文件中描述了 HTTP endpoint 與 API key 認證方向，這作為 roadmap 是合理的；  
但實際落地成熟度需要持續比對實作，不能只以設計文件為準。

---

## 目前最重要的專案定位

截至目前，最準確的說法是：

> local-coding-agent 已完成安全編輯底座、主要工具鏈與初步控制層，正從「可用工具系統」演進為「更成熟的本地代理後端」。

---

## 下一階段 roadmap（重整版）

### 高優先
1. 強化 ExecutionController
2. 明確化 retry / stop / fallback policy
3. 強化 validation policy 分級
4. 整理 Continue 體驗與流程一致性
5. 持續同步文件與實作狀態

### 中優先
1. 補強 patch generation 與 stage 流程
2. 補強對話記憶與狀態追蹤
3. 補強高階 refactor 工具
4. 補強專案命令偵測與驗證自動化

### 中長期
1. 更成熟的 Planner
2. 更成熟的 Patch Generator
3. 更成熟的 Validation Controller
4. HTTP / API 產品化
5. CI/CD 與品質門檻整合

---

## 維護原則

未來若再次更新本檔，請優先遵守以下原則：

1. 先以實測結果為準，再整理文字
2. 若文件與 code 不一致，必須明確標示「哪一份落後」
3. 重大狀態修正一定要寫入 changelog
4. 測試數量、關鍵工具與主線 workflow 不可只憑印象更新
5. 需讓未來維護者能直接看出：
   - 過去做了什麼
   - 現在做到哪裡
   - 下一步要做什麼
