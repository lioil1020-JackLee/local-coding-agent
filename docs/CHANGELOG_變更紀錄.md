# CHANGELOG 變更紀錄

## 2026-03-19 - 專案文件定位正式升級為本地端 CLI Agent + Skill System

### 這次文件更新做了什麼
這次更新的重點不是修改零散字句，而是**統一整個專案文件的北極星**。

原本許多文件雖然已經清楚記錄：
- safe-edit pipeline
- session sandbox
- validation / diff / rollback
- ExecutionController 相容層
- session lifecycle phase 1

但整體敘事仍多半把專案描述為：
- coding agent backend
- 安全修改流程
- MCP tool + pipeline 架構
- 持續演進中的 execution system

這些描述沒有錯，但已不足以代表現在專案真正想前進的方向。

### 新的終極目標
本專案文件現已明確統一為：

> **本地端 CLI Coding Agent（具備 Skill 系統），並以功能可媲美 Cursor Agent 為終極目標。**

### 為什麼要做這次更新
原因有三個：

1. **避免定位過低**
   若文件只停留在 backend / pipeline / tools 層級，未來實作容易侷限在局部工程改善，而不是往完整 agent product 演進。

2. **讓未來設計決策有共同北極星**
   包含 controller、planner、CLI UX、skill abstraction、Continue integration，都需要共同產品目標來約束方向。

3. **讓跨對話 handoff 更準確**
   未來新助理若只看文件，應能立刻理解這不只是安全編輯系統，而是朝完整 CLI agent 演進中的產品。

### 這次文件更新的主要方向
- 將「backend / tools / pipeline」敘事升級為「CLI agent / runtime / skills」
- 將「Continue integration」從主中心重新定位為介面層之一
- 將「ExecutionController 相容層」明確標示為過渡性穩定邊界，而非最終終局
- 將「session lifecycle」從維護性功能提升為 CLI agent 長期運作的必要能力
- 在多份文件中補入 skill system 與 Cursor Agent 對標定位

### 目前穩定基準仍不變
文件方向升級，不代表現有穩定基準被推翻。  
目前已知穩定基準仍然是：

- `uv run pytest`
- **28 passed in 15.82s**

### 更新後對未來工作的含義
未來所有設計與實作應以以下順序思考：

1. 這是否有助於 CLI agent 化？
2. 這是否可以 skill 化或納入 skill system？
3. 這是否維持 safe-by-default？
4. 這是否讓能力朝 Cursor Agent 等級收斂？
5. 這是否破壞既有 working baseline？

### 下一步建議
1. 先把文件與命名全面收斂
2. 建立 skill abstraction 與 skill registry 基礎
3. 在相容穩定層上建立更明確的 planner / executor agent loop
4. 強化 CLI product surface
5. 最後再深化 Continue / IDE integration
