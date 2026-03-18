# local-coding-agent

## 專案終極目標

本專案的終極目標已正式定義為：

> **打造一個本地端 CLI Coding Agent（具備 Skill 系統），並以功能可媲美 Cursor Agent 為目標。**

這代表本專案不再只是安全修改程式碼的 backend、MCP 工具集合，或單一 pipeline 實驗，而是要逐步演進成一個可在本地端執行、可擴充、可組合、可驗證、可回復的完整 agent 系統。

---

## 產品定位

本專案應被理解為：

- **本地端優先（local-first）**
- **CLI 優先（CLI-first）**
- **Agent 優先（agent-first）**
- **Skill 驅動（skill-enabled）**
- **安全修改預設（safe-by-default）**

最終狀態下，它應具備下列特徵：

1. 能從自然語言任務理解使用者意圖  
2. 能分析 codebase 並規劃多步驟修改  
3. 能在 sandbox/session 中安全執行修改  
4. 能顯示 diff、執行 validation、必要時 rollback  
5. 能透過可重用的 skill 擴充能力  
6. 能從 CLI 直接完成主要工作流  
7. 能在能力與體驗上朝 **Cursor Agent 等級** 靠攏  

---

## 最終應具備的能力

### 1. CLI Agent 能力
- 接受自然語言任務
- 自動規劃與拆解步驟
- 支援互動式與非互動式執行
- 可追蹤執行狀態與結果

### 2. Codebase 理解能力
- 理解專案結構與模組關係
- 進行語意搜尋與安全導航
- 支援多檔案修改與較大範圍重構

### 3. 安全修改能力
- 所有修改預設於 sandbox/session 內執行
- 提供 diff 預覽
- validation 失敗時可中止或 rollback
- 保留 session metadata 作為單一真實來源

### 4. Skill 系統
- 能定義 skill
- 能發現、選擇與執行 skill
- 能做 skill chaining / 組合式工作流
- 未來可擴展成 skill library

### 5. Agent Runtime
- planner / executor / validator / recovery loop
- retry / fallback / stop policy
- trace 與狀態追蹤
- 與現有 orchestrator / controller 架構平滑演進

### 6. Session Lifecycle
- session 建立、恢復、釘選、清理
- TTL + LRU 控制磁碟空間
- 與 validation / rollback / status 流程整合

---

## 目前狀態與演進原則

目前專案已具備 safe-edit pipeline、session sandbox、diff、validation、rollback、status、ExecutionController 相容層與 session lifecycle phase 1 等基礎。

但文件與定位需要統一更新：  
**未來所有設計、實作與文件，都應以「本地端 CLI Agent（具備 Skill）並朝 Cursor Agent 等級能力前進」為最高方向。**

這也代表：

- tools 不再只是 tools，而應逐步 skill 化
- pipeline 不只是流程，而應逐步演進為 agent execution graph
- CLI 不只是輔助入口，而是主要產品介面
- Continue / IDE integration 是重要介面層，但不再是唯一重心

---

## 建議開發優先順序

1. 統一文件與架構目標
2. 建立 skill abstraction
3. 補強 ExecutionController / planner / executor agent loop
4. 強化 CLI UX 與主流程入口
5. 持續深化 session lifecycle 與安全機制
6. 最後再擴充 IDE / Continue 深整合

---

## 一句話版本

> **local-coding-agent = 本地端、CLI-first、具備 Skill 系統的 coding agent，目標是逐步做到可媲美 Cursor Agent 的完整能力。**
