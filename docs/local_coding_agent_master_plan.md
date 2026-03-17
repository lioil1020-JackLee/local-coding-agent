# local-coding-agent Master Plan v2

## 這份文件是做什麼的
這是目前最重要的總說明文件。新對話接手時，請優先先看這份。

這份文件的目的，是讓新對話快速知道：
- 專案真正目標
- 現在做到哪裡
- 目前採用哪套架構
- 下一步最應該做什麼
- 我們要怎麼合作

## 專案目標
我要做的是一個：

**本地端、以 Cursor-like 體驗為目標的 coding agent**

而且目標不是做一個勉強能跑的小玩具，也不是一直補 patch，
而是要做成：
- 正式可用
- 架構完整
- 長期可維護
- 對新手友善
- 能用白話文下指令
- 儘量接近 Cursor 那種 agent 體驗

## 核心要求（固定不變）
1. 使用者是不會寫程式的新手，但有邏輯概念
2. 對話一律使用繁體中文
3. 程式碼註解也一律使用繁體中文
4. 使用者可以用模糊、白話、非工程師語言下指令
5. Agent 要能自己找檔案、找入口點、理解 repo、規劃步驟
6. 分析時絕對不能亂改檔
7. 修改時不能把聊天文字、說明文字寫進程式
8. 修改後要自動驗證，必要時要能回滾
9. 目標體驗要盡量逼近 Cursor，而不是只靠 prompt 的半套方案

## 目前正式方向
目前正式方向不是「一個超大工具一次做完所有事」，而是：

**高階理解 + 安全修改流程 + sandbox + 驗證 + 回滾**

也就是：
使用者說人話
→ Agent 先判斷意圖
→ 先規劃要做什麼
→ 再走安全修改流程
→ 先看 diff
→ 再驗證
→ 必要時回滾

## 目前架構（2026-03）
### 1. Continue / 對話層
負責：
- 接收使用者白話需求
- 分析任務與修改任務分流
- 優先走高階 agent 入口
- 把修改需求導向安全修改流程

### 2. ConversationOrchestrator
負責：
- 判斷意圖
- 分析是唯讀還是修改
- 建立計畫（plan）
- 把請求交給後面的執行層

### 3. AgentPlanner
負責：
- 把需求整理成步驟
- 定義目前應該走的流程
- 讓系統不是只靠模型自由發揮

### 4. Execution / Edit 層
目前以 `EditExecutionOrchestrator` 為主。
負責：
- 建立 session
- 使用 copy-based sandbox
- 套用修改
- 產生 diff
- 跑 validation
- 寫回 session metadata

### 5. Sandbox Runtime
目前已從容易 timeout 的 git worktree 主線，
改成 **copy-based sandbox 主線**。

## 目前已完成
### MCP / repo_guardian 相關
- 已有高階工具：
  - `preview_user_request_plan_tool`
  - `handle_user_request_tool`
- 已有低階安全修改工具：
  - `create_task_session_tool`
  - `edit_file_tool`
  - `preview_session_diff_tool`
  - `run_validation_pipeline_tool`
  - `rollback_session_tool`

### 安全修改流程
目前可運作主線：
1. 預覽計畫
2. 建立 session
3. 建立 copy-based sandbox
4. 修改 sandbox 中的檔案
5. 預覽 diff
6. 執行 validation
7. 必要時回滾

### 測試狀態
- `pytest`：**14 passed**

### Continue 狀態
- 分析任務已能走高階 agent 入口
- 修改任務已能走 session workflow
- README 實際修改流程已測通

## 目前明確採用的技術決策
### 決策 1：不用 git worktree 當主要 sandbox
原因：
- Continue MCP tool call 容易 timeout
- worktree 建立太慢
- rollback 也容易被拖慢
所以目前改採：
**copy-based sandbox**

### 決策 2：分析與修改必須分開
正式原則：
- 分析 → 唯讀
- 修改 → 一定走安全 session workflow

### 決策 3：高階入口與低階工具並存
- 高階入口負責理解與規劃
- 低階工具負責穩定執行

## 目前尚未完成，但下一步非常重要的事
### 1. ExecutionController
下一個最重要的大項。
目標：
- step-by-step 執行
- retry guard
- stop guard
- fallback policy
- 不要亂重試
- 不要失敗後跳去做不相干的事

### 2. idempotent edit
目前已觀察到 append 重複內容的現象。
之後要補：
- append_if_missing
- replace_once
- 避免重複寫入相同內容

### 3. validation policy 分級
之後要做成：
- README / Markdown 類修改 → 輕量檢查
- Python 類修改 → pytest / lint / 更嚴格檢查
- config 類修改 → 格式檢查

### 4. Continue 體驗再收斂
後續要再收斂：
- 回覆更少廢話
- 工具選擇更穩
- 失敗時不要亂 fallback
- 讓 builder 行為更穩定

## 正式實作順序（建議）
### Phase 1：先把現在能跑的版本收斂穩
- 補 idempotent append / replace
- 補 retry guard
- 補 stop guard
- 補更穩定的 diff / validation contract

### Phase 2：補 ExecutionController
- 把目前的 step 執行正式化
- 不讓模型自己亂串工具
- 每一步都做結果檢查

### Phase 3：validation policy 升級
- 讓不同修改類型走不同驗證策略

### Phase 4：Continue 體驗收斂
- planner / builder 分工更清楚
- 更像 Cursor 的操作手感

### Phase 5：更進一步的正式能力
- multi-file edit
- smarter patch planning
- 自動提交摘要
- 更完整的 change report

## 我們的合作方式（固定規則）
### 合作原則
- 不要只講概念，盡量直接改檔
- 不要叫使用者自己想太多工程細節
- 需要什麼檔案，直接點名要哪個檔
- 改完後直接提供下載連結
- 使用者把檔案覆蓋回本地專案
- 使用者照指示測試
- 測試通過，再進下一步

### 固定節奏
1. 先定位一個檔案或一小組檔案
2. 直接修改
3. 提供下載連結
4. 使用者本地覆蓋
5. 跑 pytest 或指定測試
6. 回報結果
7. 再進下一步

## 新對話接手時建議先讀的文件
1. `docs/local_coding_agent_master_plan.md`
2. `docs/DEVELOPMENT_STATUS.md`
3. `docs/workflow.md`
4. `docs/continue-setup.md`
5. `docs/cursor_style_notes.md`
6. `docs/collaboration_protocol.md`
7. `README.md`

## 給未來新對話的快速接手提示
如果在新對話裡要快速接手，請先假設：
- 目前 repo_guardian 已可跑通 session workflow
- copy-based sandbox 已是主線
- pytest 目前全綠（14 passed）
- Continue 已能跑分析與修改主線
- 下一步重點不是再修大架構，而是做正式化收斂：
  - ExecutionController
  - idempotent edit
  - validation policy
  - Continue 體驗收斂
