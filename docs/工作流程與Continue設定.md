# 工作流程與 Continue 設定

本文件介紹代理系統的工作流程以及 VSCode Continue 外掛的設定方式，方便使用者快速上手。  

## 工作流程

代理提供分析與編輯兩種主要任務，皆以 `run_task_pipeline` 為統一入口：

- **分析任務**：呼叫 `run_task_pipeline(task_type=analyze)`，由 TaskOrchestrator 組合步驟，進行 repo 概覽、搜尋關鍵字或讀取程式碼區段等唯讀操作。分析步驟不會產生任何副作用。  
- **編輯任務**：呼叫 `run_task_pipeline(task_type=edit)`，任務將依序執行：  
  1. **建立 session**：使用 `create_task_session` 建立 sandbox 工作區。  
  2. **產生補丁**：呼叫 `propose_patch`，由語言模型生成修改建議，可處理多檔案與重構。  
  3. **預覽 diff**：使用 `preview_diff` 在記憶體套用 patch，顯示 unified diff 給使用者確認。  
  4. **套用 patch**：使用 `stage_patch` 寫入檔案；必要時可搭配 `move_file`、`rename_symbol` 等高階工具。  
  5. **執行驗證**：透過 `run_validation_pipeline` 執行語法檢查、pytest 測試與自訂驗證規則。若驗證失敗，將回滾修改。  
  6. **持久化或回滾**：驗證通過後 persist session；否則執行 `rollback_session`。  
  
每個步驟由 `ExecutionController` 管理，其負責正規化輸入輸出、處理 retry/stop/fallback 策略，並生成 `execution_trace` 供追蹤。  

## Continue 設定

欲在 VSCode 使用 Continue 外掛操控代理，需準備以下設定：

- 在 `.continue/config.json` 中設定 MCP server 位址與可用工具，例如：

```json
{
  "serverUrl": "http://localhost:8000",
  "tools": [
    { "name": "Run Task", "endpoint": "/run_task_pipeline", "description": "分析或編輯檔案" },
    { "name": "Create Session", "endpoint": "/tools/create_task_session", "description": "建立隔離工作區" },
    { "name": "Propose Patch", "endpoint": "/tools/propose_patch", "description": "產生修補建議" },
    { "name": "Preview Diff", "endpoint": "/tools/preview_diff", "description": "預覽 unified diff" },
    { "name": "Stage Patch", "endpoint": "/tools/stage_patch", "description": "套用 patch 至 sandbox" },
    { "name": "Run Validation", "endpoint": "/tools/run_validation_pipeline", "description": "執行驗證" },
    { "name": "Move File", "endpoint": "/tools/move_file", "description": "移動或重新命名檔案" },
    { "name": "Rename Symbol", "endpoint": "/tools/rename_symbol", "description": "重新命名符號 (規劃中)" },
    { "name": "Extract Function", "endpoint": "/tools/extract_function", "description": "擷取函式 (規劃中)" }
  ]
}
```

- 在啟動 MCP server 之前，請設定環境變數 `MCP_API_KEY`。呼叫任何工具時，需在 HTTP 標頭加入 `X-API-Key` 進行認證。  
- 若需要手動控制流程，可依序使用 `create_task_session` → `propose_patch` → `preview_diff` → `stage_patch` → `run_validation_pipeline` → `rollback_session`（若失敗）。這些工具皆可從 Continue 的工具面板直接調用。  
- `run_task_pipeline` 是最簡單的入口，只需傳入 `task_type` 即可完成分析或編輯任務。  

透過上述設定，即可在 VSCode 中以自然語言控制代理，並於介面中看到 diff 預覽、驗證結果與回滾選項。