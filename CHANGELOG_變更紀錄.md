# CHANGELOG（更新版）

## Latest：ExecutionController 對齊完成

### 新增
- ExecutionController（step orchestration）
- StepResult / Retry / Fallback

### 修正
- validation.status → pass/fail
- session status 寫回錯誤
- session_file 型別錯誤（dict → str）

### 測試
- 23 passed

### 架構
- pipeline control 與 tools 解耦
- session workflow 成主線
