# Trace Summary Progress (Phase 4.2)

## 🎯 目標
將 internal execution trace 轉換為 user-facing、可解釋的 CLI 輸出，並建立 single source of truth。

---

## ✅ 已完成（Phase 4.2）

### 1. Execution Trace Pipeline
已建立完整 execution trace：

- preview_plan
- select_skill
- execute_skill
- validate_skill
- finalize

每個 step 包含：
- step_id
- step_type
- status
- retry_count
- error

---

### 2. Trace Summary Service

新增：

- TraceSummaryService

輸出：

- trace_summary（結構化）
- trace_summary["text"]（canonical text）
- trace_summary_text（mirror）

---

### 3. Single Source of Truth（SSOT）

已統一：

- trace_summary["text"]
- trace_summary_text
- display_message

規則：

display_message 必須直接使用 trace_summary_text，不可自行拼接。

---

### 4. CLI Integration

chat / run / status 均已整合 trace summary 顯示。

---

### 5. Validation Integration

validate_skill 已整合為：

- 驗證結果：成功

並納入 summary。

---

### 6. 測試狀態

pytest -q
78 passed

---

## ⚠️ 未完成（Phase 4.2.x）

### Trace Output Normalization 問題

目前仍存在：

#### 1. 字串污染（spacing 問題）
- -  整理輸出
- 多餘空格

#### 2. 中文斷裂
- 成 功
- 驗證結 果

#### 3. step_label 不穩定
- 有時被污染
- 與最終 line 不一致

---

## 🎯 下一步（Phase 4.2.x）

### 目標
建立 canonical trace text normalization

### 要求

1. trace_summary["text"] 必須唯一正確來源
2. display_message 僅使用 trace_summary_text
3. step_label 不可被破壞
4. 統一格式：

- 驗證結果：成功

### 禁止事項

- 不可修改 cli_agent_service 大結構
- 不可重寫 CLI pipeline
- 不可破壞現有測試

---

## 🧪 待補測試

建議新增：

- 禁止出現：
  - 成 功
  - 驗證結 果
  - -  （雙空格）
- trace_summary_text == display_message substring
- step_label == canonical label

---

## 🧠 結論

Phase 4.2：

- 架構完成
- trace → summary → CLI 全串接
- output formatting 尚未收斂

下一階段重點：

小範圍 normalization 修正（高穩定、低風險）
