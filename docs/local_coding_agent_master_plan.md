# Local Coding Agent 總計畫書

更新日期：2026-03-16

## 1. 專案目標

打造一個 **本地端、正式可用、以 Cursor-like 體驗為目標** 的 coding agent，而不是只靠 prompt 撐起來的半套方案，也不是只做最小可用版後一直補 patch。

### 核心要求
1. 使用者是不會寫程式的新手，但有邏輯概念  
2. 對話必須使用繁體中文，程式碼註解也使用繁體中文  
3. 能接受模糊、白話、非工程師語言指令  
4. Agent 要能自己找檔案、找入口點、理解 repo、規劃步驟  
5. 分析時絕對不能亂改檔  
6. 修改時不能把聊天文字、說明文字寫進程式  
7. 修改後要自動驗證，必要時可回滾  
8. 目標體驗要盡量逼近 Cursor 類型 agent，而不是只靠 prompt 的半套方案  

---

## 2. 目前環境

- 編輯器：VSCode + Continue
- 模型服務：LM Studio
- 主模型：`qwen/qwen2.5-coder-14b-instruct`
- Embeddings：`text-embedding-nomic-embed-text-v1.5`
- MCP：
  - github（已成功）
  - filesystem（已成功）
  - repo_guardian（已接入）
- GitHub Token 環境變數：`GITHUB_TOKEN`

### Continue 實際生效設定
目前實際 Continue 執行時吃的是：

- `F:\.continue\config.yaml`

不是 repo 內的：

- `E:\py\local-coding-agent\continue\config.yaml`

因此：
- `F:\.continue\config.yaml` = 正式 runtime config
- repo 內 `continue/config.yaml` = 建議保留為版本化 template / 設計稿

---

## 3. 目前已知專案現況

根據已提供的檔案，目前可以確認：

### 已存在
- Continue 設定與角色分工
- `repo_guardian` MCP server
- repo 分析工具
- patch proposal / diff preview 工具
- `TaskOrchestrator` 雛形
- sandbox session 概念
- validation hook 雛形
- 測試已可跑通（先前紀錄為 pytest 已通過）

### 目前主要瓶頸
1. builder 行為仍可能退回 Continue 內建編輯，而不是穩定走 repo_guardian flow
2. `TaskOrchestrator` 現在比較像單次 pipeline，不是完整高階 orchestrator
3. 安全規則目前仍有一部分只靠 prompt，而不是靠系統保證
4. validation 還是偏 v1，離正式可用還差一段
5. apply / rollback contract 尚未完整定義

---

## 4. 正式版架構藍圖

系統應拆成 5 層：

### A. Continue 對話層
負責：
- 接收使用者白話指令
- 顯示分析、計畫、diff、驗證結果
- 呼叫 MCP server 與模型角色

### B. Orchestrator 決策層
負責：
- 判斷使用者意圖
- 判斷是分析模式還是修改模式
- 選擇工具流程
- 控制 session lifecycle
- 統一輸出結果給 Continue

### C. Repo Intelligence 層
唯讀能力：
- repo overview
- entrypoints
- search codebase
- code region
- symbol index
- impact analysis

### D. Safe Edit Pipeline 層
負責：
- create session
- propose patch
- preview diff
- validate
- apply
- rollback

### E. Workspace / Git 層
負責：
- 真正 repo
- sandbox / worktree
- session metadata
- diff artifact
- validation report

---

## 5. Orchestrator 正式設計

正式版不應只有一個 `TaskOrchestrator`，而應拆成兩層：

### 5.1 ConversationOrchestrator
高階任務決策器。

#### 職責
- 解析白話需求
- 判斷意圖：
  - project_analysis
  - code_explanation
  - patch_planning
  - patch_generation
  - patch_apply
  - validation_only
  - rollback
- 決定使用：
  - `qwen25-main`
  - `qwen25-builder`
- 控制是否進入唯讀模式或修改模式

#### 原則
- 預設唯讀
- 沒有明確修改意圖，不得修改檔案
- 使用者可用非工程語言描述需求

### 5.2 EditExecutionOrchestrator
低階安全修改執行器。

#### 職責
- 建立 session
- 建立 sandbox
- 收 patch proposal
- 套用至 sandbox
- 產生 diff
- 執行 validation
- 控制 apply / rollback
- 回寫 session 狀態

---

## 6. MCP 工具正式分層

### 6.1 Repo Analysis Tools（唯讀）
- `analyze_repo_tool`
- `get_repo_overview`
- `get_entrypoints`
- `search_codebase`
- `get_code_region`
- `get_symbol_index`
- `get_impact_analysis`

### 6.2 Patch Planning Tools
- `propose_patch_tool`
- `preview_diff_tool`

### 6.3 Session / Sandbox Tools（正式版應補齊）
- `create_task_session_tool`
- `get_session_status_tool`
- `list_session_files_tool`
- `preview_session_diff_tool`
- `discard_session_tool`
- `rollback_session_tool`

### 6.4 Validation / Apply Tools（正式版應補齊）
- `run_validation_tool`
- `apply_session_patch_tool`
- `rollback_session_tool`
- `finalize_session_tool`

---

## 7. 安全編輯機制

### 原則 1：分析與修改必須分離
- 分析工具全部唯讀
- 修改工具只能在 session sandbox 操作
- 禁止模型直接修改正式 workspace

### 原則 2：LLM 不直接自由寫檔，只能提交結構化 patch
建議使用結構化 patch schema，而不是自由輸出整段檔案內容。

### PatchOperation 建議格式
```python
@dataclass
class PatchOperation:
    op: Literal["replace", "insert_after", "insert_before", "append", "create_file"]
    file_path: str
    target: str | None
    content: str
    reasoning: str | None = None
```

### 原則 3：禁止把聊天文字寫進程式
需加入 policy / validation：
- 禁止出現「以下是修改說明」
- 禁止把 markdown 條列或聊天說明寫進程式檔
- 註解需為繁體中文且符合註解規範

### 原則 4：所有修改先進 sandbox，再決定 apply
固定流程：
1. create session
2. generate patch
3. apply to sandbox
4. preview diff
5. validate
6. apply
7. rollback if needed

---

## 8. 驗證機制

正式版應採多層驗證：

### Level 1：Patch Integrity
- patch 可套用
- target text 存在
- diff 非空
- 沒改到禁止路徑

### Level 2：Policy Validation
- 禁止修改關鍵系統目錄
- 禁止超過最大改檔數
- 禁止未授權新增檔案
- 禁止聊天說明文字寫入 code
- 註解需符合繁中規則

### Level 3：Static Validation
- `python -m compileall`
- `ruff`
- `mypy`（可選）

### Level 4：Project Validation
- `pytest`
- smoke test
- entrypoint test

### Level 5：Session Summary
輸出：
- 改了哪些檔案
- 風險說明
- 驗證結果
- 是否允許 apply

### 建議 ValidationPolicy
```python
@dataclass
class ValidationPolicy:
    max_files_to_change: int = 5
    allow_new_files: bool = False
    require_tests: bool = True
    require_python_compile: bool = True
    forbid_chatty_text_in_code: bool = True
    forbid_tool_dir_changes: bool = True
```

---

## 9. Continue 設計原則

### 模型分工
#### `qwen25-main`
只做：
- repo 導覽
- 架構分析
- 找入口點
- 規劃修改
- 風險說明

#### `qwen25-builder`
只做：
- 結構化 patch proposal
- diff 解讀
- 驗證結果整理
- 在 orchestrator 指示下執行安全修改

### 原則
- prompt 保留語言規則與大原則
- 流程保證下放到 orchestrator / tool layer
- 不可只靠 prompt 保證安全

### Continue 端建議補強
- builder 不得優先使用內建編輯能力
- 遇到修改任務時，必須優先走 repo_guardian session-based flow
- 新增 orchestrator mode prompt
  - 專案分析模式
  - 修改規劃模式
  - 安全修改模式
  - 驗證與回滾模式

---

## 10. 正式版目錄建議

```text
local-coding-agent/
├─ continue/
│  ├─ prompts/
│  │  ├─ analysis.md
│  │  ├─ builder.md
│  │  └─ orchestrator.md
│  ├─ rules/
│  │  ├─ zh_tw.md
│  │  ├─ analysis_first.md
│  │  └─ safe_editing.md
│  └─ config.template.yaml
│
├─ repo_guardian_mcp/
│  ├─ server.py
│  ├─ settings.py
│  ├─ schemas/
│  │  ├─ patch_models.py
│  │  ├─ session_models.py
│  │  └─ validation_models.py
│  ├─ tools/
│  │  ├─ analyze_repo.py
│  │  ├─ repo_overview.py
│  │  ├─ find_entrypoints.py
│  │  ├─ search_code.py
│  │  ├─ read_code_region.py
│  │  ├─ symbol_index.py
│  │  ├─ impact_analysis.py
│  │  ├─ create_task_session.py
│  │  ├─ propose_patch.py
│  │  ├─ preview_diff.py
│  │  ├─ apply_session_patch.py
│  │  ├─ rollback_session.py
│  │  ├─ validate_session.py
│  │  └─ get_session_status.py
│  ├─ services/
│  │  ├─ conversation_orchestrator.py
│  │  ├─ edit_execution_orchestrator.py
│  │  ├─ patch_engine.py
│  │  ├─ sandbox_manager.py
│  │  ├─ validation_service.py
│  │  ├─ policy_guard_service.py
│  │  └─ session_store.py
│  └─ utils/
│     ├─ path_guard.py
│     ├─ diff_utils.py
│     └─ text_safety.py
│
├─ agent_runtime/
│  ├─ sessions/
│  ├─ sandboxes/
│  ├─ diffs/
│  └─ validation_reports/
│
├─ tests/
│  ├─ test_analysis_tools.py
│  ├─ test_patch_engine.py
│  ├─ test_validation_service.py
│  ├─ test_orchestrator_routing.py
│  └─ test_session_lifecycle.py
│
├─ docs/
│  ├─ architecture.md
│  ├─ tool_contracts.md
│  ├─ safety_policy.md
│  └─ continue_integration.md
│
└─ pyproject.toml
```

---

## 11. MCP Server 骨架方向

原則：
- `server.py` 保持薄層
- tool 只做 transport / entry
- 真正邏輯放 service

應建立：
- `RepoAnalysisService`
- `ConversationOrchestrator`
- `EditExecutionOrchestrator`
- `ValidationService`
- `SandboxManager`
- `PatchEngine`

---

## 12. 實作順序（正式版，不是 MVP）

### Phase 1：基礎重構
1. 將 `server.py` 變薄
2. 將 `TaskOrchestrator` 拆為：
   - `ConversationOrchestrator`
   - `EditExecutionOrchestrator`
3. 補 session lifecycle 工具
4. 補 policy guard

### Phase 2：建立正式安全編輯鏈
1. 結構化 patch schema
2. deterministic patch engine
3. preview diff
4. validate
5. apply / rollback

### Phase 3：升級 validation pipeline
1. compile check
2. lint
3. pytest
4. policy checks
5. validation report

### Phase 4：Continue 整合優化
1. 精簡 prompt
2. builder 行為限制
3. 統一 session status 輸出
4. 降低退回內建編輯機率

### Phase 5：體驗逼近 Cursor
1. 修改前計畫摘要
2. diff 摘要
3. 驗證摘要
4. rollback 入口
5. repo 導覽體驗優化

---

## 13. 目前進度狀態

### 已完成
- 明確定義最終目標：本地端、正式可用、Cursor-like coding agent
- 明確定義環境與限制
- 已確認 Continue 實際 runtime config 是 `F:\.continue\config.yaml`
- 已確認 repo_guardian 已接入 Continue
- 已確認現有 MCP tools 與 `TaskOrchestrator` 雛形存在
- 已完成正式版架構藍圖
- 已完成正式版分層設計
- 已完成安全編輯與驗證機制設計方向
- 已完成正式版目錄與實作順序規劃

### 未完成
- `TaskOrchestrator` 拆分為正式雙層 orchestrator
- session lifecycle 工具補齊
- 結構化 patch schema 實作
- deterministic patch engine 實作
- 多層 validation pipeline 實作
- apply / rollback contract 完整化
- Continue prompt / config 正式重整
- 正式版文件與測試補齊

### 下一步最優先
1. 重構 `task_orchestrator.py`
2. 將 `server.py` 薄層化
3. 補 session / validation / rollback 工具契約
4. 把安全規則從 prompt 下放到 service layer

---

## 14. 下次新對話時建議怎麼開場

你可以直接把這份檔案丟進新對話，然後附上這段：

> 這是我們上一輪整理好的 local coding agent 總計畫書。  
> 請直接以這份計畫為基礎延續，不要回到 MVP 思維。  
> 目標是正式可用、長期維護、Cursor-like 體驗。  
> 接下來請先協助我重構 orchestrator 與 MCP tool contract。

---

## 15. 關於記憶與跨對話延續

### 我能做的
- 在這個對話裡持續根據上下文延續
- 幫你整理成可丟進新對話的計畫書
- 用這份計畫書作為跨對話交接文件

### 目前限制
我無法保證把這次所有新細節都永久存成跨對話記憶。  
因此最穩定的方法就是：

1. 保留這份計畫書  
2. 新對話直接上傳  
3. 再加上最新檔案（例如 `server.py`、`task_orchestrator.py`、`config.yaml`）

這樣新的對話就能很快進入狀況，不必從零開始。

---

## 16. 建議你長期維護的交接檔

之後可以固定維護一份：

- `docs/master_plan_local_coding_agent.md`

每次重要進展就更新：
- 已完成
- 正在進行
- 下一步
- 架構決策變更
- 目前卡點

這會是你最穩的跨對話交接方法。
