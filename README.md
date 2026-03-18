# local-coding-agent

本專案是一個以 **本地端、可控、安全、可追溯** 為核心原則的 Coding Agent / Repo Guardian MCP Server 實驗專案。

它的長期目標不是單純做出一個「可以改檔」的 prompt demo，而是要逐步建立一套真正能長期維護、能與 Continue 等前端整合、能讓不會寫程式的人也可安全使用的 **Cursor-like 本地編輯代理系統**。

---

## 一、這個專案目前在做什麼

本專案目前已經完成一套可運作的基礎能力，核心重點在於：

1. **分析與修改流程分離**
   - 分析任務盡量維持唯讀。
   - 修改任務必須進入安全編輯流程，不直接污染原始 repo。

2. **以 session / sandbox 為核心的安全修改**
   - 每次修改建立獨立 session。
   - 在 sandbox 中編輯、預覽 diff、執行驗證。
   - 驗證失敗可回滾。

3. **MCP 工具化**
   - 將編輯、diff、驗證、回滾、分析等能力拆成多個 MCP tools。
   - 降低單一大型工具造成的 timeout 與失控風險。

4. **朝 agent backend 演進**
   - 已不只是「工具集合」。
   - 已開始有 ExecutionController、規劃與補丁生成的雛形。
   - 但仍未到完整多輪代理與完整 HTTP 產品化階段。

---

## 二、目前實際狀態摘要（依目前實測與文件整合）

### 已確認成立

- `uv run pytest` 目前 **18 項測試全部通過**
- `python -m repo_guardian_mcp.server` 可啟動，且以 **stdio 型 MCP server** 形式待命
- Continue 設定已統一，並以 `config.yaml` 導向 repo_guardian MCP server
- session workflow 已成為主線
- ExecutionController 已有初步實作與測試覆蓋
- 分析工具、validation、rollback、run_task_pipeline 等核心能力已存在

### 目前比較準確的定位

這個專案目前不是：
- 只有文件、沒有程式
- 或只有一堆零散工具

而是：

> **已完成安全編輯底座與主要工具鏈，正從「可用的工具系統」進一步演進成「更完整的代理後端」。**

---

## 三、目前推薦理解這個專案的方式

可以把整體架構理解成下面這條鏈：

```text
使用者
↓
Continue / 對話前端
↓
config.yaml（規則、模型、工作流程限制）
↓
repo_guardian MCP tools
↓
ExecutionController / Orchestrator
↓
Services
↓
Sandbox / Session / Validation / Rollback
```

### 各層說明

#### 1. Continue / 前端層
負責接收自然語言需求，並依設定決定：
- 目前是分析任務還是修改任務
- 應先走哪些工具
- 哪些工具要避免（例如過大的 mega-tool 流程）

#### 2. config.yaml
這一層很重要，因為它不只是模型設定，還包含：
- 分析優先（analysis-first）
- 專案導覽模式
- session workflow 規則
- 針對 repo_guardian MCP tools 的使用規範
- builder / main 模型分工

#### 3. MCP tools
這一層將能力拆成單一責任工具，例如：
- 建立 session
- 編輯檔案
- 預覽 diff
- 驗證
- 回滾
- 分析 repo
- 搜尋程式碼
- 產生 patch proposal

#### 4. ExecutionController / Orchestrator
這一層開始扮演「流程控制」角色：
- 控制步驟順序
- 管理狀態
- 統一輸入輸出
- 為未來 retry / stop / fallback 策略預留位置

#### 5. Services
真正執行核心邏輯的地方，例如：
- sandbox service
- validation service
- rollback service
- planning / patch / repo scan / symbol service 等

#### 6. Sandbox / Session / Validation
這是整個專案目前最成熟的區塊：
- 所有寫入集中在 sandbox
- 每次任務有 session 狀態
- 可以產生 diff
- 可以驗證
- 可以 rollback

---

## 四、目前主要能力

### 1. 安全編輯工作流
目前最穩定、最可依賴的能力是以下流程：

```text
preview plan
→ create session
→ edit sandbox
→ preview diff
→ run validation
→ rollback（必要時）
```

這是目前專案最重要的主線能力。

### 2. 分析能力
已具備基本的 repo 分析工具，例如：
- repo overview
- search codebase
- 入口點搜尋
- 局部程式區段分析

### 3. 補丁與 diff 流程
目前已可支援：
- patch proposal
- diff preview
- stage patch
- session diff preview

### 4. 驗證與保護
目前已有：
- validation pipeline
- text / semantic guard 類型保護
- rollback

---

## 五、目前文件與實際狀態之間的重要修正

在整理現況時，已確認舊文件有幾個地方落後：

1. 舊文件仍寫 **14 passed**
   - 目前實測已是 **18 passed**

2. 舊文件曾寫 ExecutionController 尚未實作
   - 目前已有 `test_execution_controller.py`，表示至少已有初步落地實作

3. 舊文件描述「仍在從單一 pipeline 過渡到 session 架構」
   - 目前更準確的說法應是：**session workflow 已成為主線，舊 mega-tool 思維正在被邊緣化**

---

## 六、目前尚未完全完成的地方

雖然專案已經有相當基礎，但以下部分仍屬於未完成或部分完成：

### 1. 完整多輪對話記憶
目前雖已有 conversation / session 的概念，但尚未成熟到完整多輪代理記憶系統。

### 2. 完整 retry / stop / fallback 策略
ExecutionController 已存在，但是否已完整實作嚴謹的 retry guard、stop guard、fallback policy，仍屬需持續強化的範圍。

### 3. 完整 HTTP / FastAPI 產品化
部分設計文件描述了 FastAPI `/run_task_pipeline` 與 `/tools/<name>` 形式的 server，但目前你實測可直接啟動的是 `python -m repo_guardian_mcp.server` 的 stdio 形態。  
因此 HTTP 型 MCP server 若要正式對外使用，仍需視實作內容再確認與補強。

### 4. 高階 refactor 工具
像是：
- rename symbol
- extract function
- move file 的成熟版本
- 更高階的 code action orchestration

仍在發展中。

### 5. 更完整驗證
未來仍應持續補強：
- flake8
- mypy
- black
- pytest 分級執行
- 自訂規則
- 專案指令偵測與驗證命令自動化

---

## 七、目前專案應該如何看待

最適合的定位是：

> **這是一個已完成核心安全底座與工具流程的本地 Coding Agent 專案，正在往更成熟的 agent backend 與前端整合產品化前進。**

它目前的重點不是再重新發明基礎工具，而是：

- 讓工具更穩
- 讓控制層更清楚
- 讓 Continue 整合更順
- 讓文件與狀態同步
- 讓未來維護者能真正看懂現況與下一步

---

## 八、建議閱讀順序

若是第一次接觸這個專案，建議閱讀順序如下：

1. `README.md`
2. `CHANGELOG.md`
3. `CONTRIBUTING.md`
4. `docs/目標與方向.md`
5. `docs/變更與進度.md`
6. `docs/工作流程與Continue設定.md`
7. `docs/設計方案.md`

之後再回頭查看：
- `project_tree.md`
- `py_file_lines.md`
- `tests/`
- `repo_guardian_mcp/services/`
- `repo_guardian_mcp/tools/`

---

## 九、下一步建議

目前最值得優先投入的方向：

1. 強化 ExecutionController 的 retry / stop / fallback
2. 進一步釐清 `run_task_pipeline` 與 session workflow 的主次角色
3. 把驗證分級並與專案命令檢測整合
4. 讓 Continue 使用體驗更穩定
5. 補齊文件，避免未來再出現「文件與程式狀態脫節」

---

## 十、結語

這個專案的真正價值，不只是讓 AI 能改檔，而是：

- 讓流程 **安全**
- 讓修改 **可追蹤**
- 讓結果 **可驗證**
- 讓失敗 **可回滾**
- 讓不會寫程式的人也能有機會使用本地代理協作開發

這也是後續所有設計、工具拆分、session workflow 與文件維護的核心理由。
