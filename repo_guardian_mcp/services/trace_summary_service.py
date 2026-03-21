from __future__ import annotations

import re
from collections import Counter
from typing import Any


_CJK = "\u4e00-\u9fff"
_ZERO_WIDTH_RE = re.compile(r"[\u200b\u200c\u200d\u2060\ufeff]")
_ESCAPED_NEWLINE_RE = re.compile(r"\\[nrt]")


class TraceSummaryService:
    """將 runtime / execution trace 整理成穩定、可顯示、可比對的 canonical 輸出。"""

    _STATUS_LABELS = {
        "success": "成功",
        "failed": "失敗",
        "error": "錯誤",
        "skipped": "略過",
        "cancelled": "取消",
        "pending": "等待中",
        "running": "執行中",
    }

    _STEP_LABELS = {
        "preview_plan": "預覽計畫",
        "select_skill": "選擇技能",
        "execute_skill": "執行技能",
        "validate_skill": "驗證結果",
        "finalize": "整理輸出",
    }

    def summarize(self, trace: list[dict[str, Any]] | None) -> dict[str, Any]:
        items: list[dict[str, Any]] = []
        counts: Counter[str] = Counter()

        for raw in trace or []:
            step_id = str(raw.get("step_id") or "")
            step_type = str(raw.get("step_type") or raw.get("step") or raw.get("event") or step_id or "unknown")
            status = str(raw.get("status") or ("success" if raw.get("ok", True) else "failed"))
            retry_count = int(raw.get("retry_count") or 0)
            error = raw.get("error")
            label = self._canonicalize_step_label(self._build_step_label(step_type))
            line = self._build_line(label=label, status=status, retry_count=retry_count, error=error)
            counts[status] += 1
            items.append(
                {
                    "step_id": step_id,
                    "step_type": step_type,
                    "step_label": label,
                    "status": status,
                    "retry_count": retry_count,
                    "error": error,
                    "line": line,
                }
            )

        summary = {
            "total": len(items),
            "success": counts.get("success", 0),
            "failed": counts.get("failed", 0),
            "error": counts.get("error", 0),
            "skipped": counts.get("skipped", 0),
            "cancelled": counts.get("cancelled", 0),
            "items": items,
        }
        return self.canonicalize_trace_summary(summary)

    def canonicalize_summary(self, summary: dict[str, Any] | None) -> dict[str, Any]:
        return self.canonicalize_trace_summary(summary)

    def canonicalize_trace_summary(self, summary: dict[str, Any] | None) -> dict[str, Any]:
        canonical = dict(summary or {})
        items: list[dict[str, Any]] = []
        counts: Counter[str] = Counter()

        for raw in list(canonical.get("items") or []):
            item = dict(raw)
            step_type = str(item.get("step_type") or item.get("step_id") or "unknown")
            status = str(item.get("status") or "success")
            retry_count = int(item.get("retry_count") or 0)
            error = item.get("error")
            label = self._canonicalize_step_label(
                str(item.get("step_label") or self._build_step_label(step_type))
            )

            item["step_label"] = label
            item["status"] = status
            item["retry_count"] = retry_count
            item["error"] = error
            item["line"] = self._normalize_line(
                self._build_line(label=label, status=status, retry_count=retry_count, error=error)
            )
            items.append(item)
            counts[status] += 1

        canonical["items"] = items
        canonical["total"] = len(items)
        canonical["success"] = counts.get("success", 0)
        canonical["failed"] = counts.get("failed", 0)
        canonical["error"] = counts.get("error", 0)
        canonical["skipped"] = counts.get("skipped", 0)
        canonical["cancelled"] = counts.get("cancelled", 0)

        text = self.build_summary_text(canonical)
        text = self._normalize_multiline_trace_text(text)
        canonical["text"] = text
        return canonical

    def canonicalize_payload(
        self,
        payload: dict[str, Any] | None,
        *,
        message: str = "",
    ) -> dict[str, Any]:
        canonical = dict(payload or {})
        trace_summary = canonical.get("trace_summary")

        if not isinstance(trace_summary, dict):
            canonical.pop("trace_summary", None)
            canonical.pop("trace_summary_text", None)
            canonical.pop("display_message", None)
            return canonical

        summary = self.canonicalize_trace_summary(trace_summary)
        canonical_text = self._normalize_multiline_trace_text(str(summary.get("text") or ""))
        summary["text"] = canonical_text
        canonical["trace_summary"] = summary
        canonical["trace_summary_text"] = canonical_text
        canonical["display_message"] = self._compose_display_message_from_canonical_text(message, canonical_text)
        return canonical

    def build_summary_text(self, summary: dict[str, Any]) -> str:
        items = list(summary.get("items") or [])
        if not items:
            existing = self._normalize_multiline_trace_text(str(summary.get("text") or ""))
            if existing:
                return existing
            return "[trace summary]\n- 目前沒有 execution trace"

        header = [
            "[trace summary]",
            f"- 總步驟：{summary.get('total', len(items))}",
            f"- 成功：{summary.get('success', 0)}",
            f"- 失敗：{summary.get('failed', 0)}",
            f"- 錯誤：{summary.get('error', 0)}",
            f"- 略過：{summary.get('skipped', 0)}",
        ]
        lines = []
        for item in items:
            line = self._normalize_line(str(item.get("line") or ""))
            if line:
                lines.append(line)

        text = "\n".join(header + lines)
        return self._normalize_multiline_trace_text(text)

    def build_display_message(
        self,
        message: str,
        trace_summary_text: str | None = None,
        *,
        trace_summary: dict[str, Any] | None = None,
    ) -> str:
        text = self._normalize_multiline_trace_text(trace_summary_text or "")
        if not text and trace_summary and isinstance(trace_summary, dict):
            existing = self._normalize_multiline_trace_text(str(trace_summary.get("text") or ""))
            text = existing or self.canonicalize_trace_summary(trace_summary).get("text", "")
        return self._compose_display_message(message, text)

    def _compose_display_message(self, message: str, text: str | None) -> str:
        normalized_text = self._normalize_multiline_trace_text(str(text or ""))
        base_message = self._normalize_text((message or "").strip())
        if not normalized_text:
            return base_message
        if not base_message:
            return normalized_text
        return f"{base_message}\n\n{normalized_text}"

    def _compose_display_message_from_canonical_text(self, message: str, canonical_text: str) -> str:
        base_message = self._normalize_text((message or "").strip())
        text = str(canonical_text or "")
        if not text:
            return base_message
        if not base_message:
            return text
        return f"{base_message}\n\n{text}"

    def _build_step_label(self, step_type: str) -> str:
        return self._STEP_LABELS.get(step_type, step_type.replace("_", " ").strip() or "unknown")

    def _build_line(self, *, label: str, status: str, retry_count: int, error: Any) -> str:
        safe_label = self._canonicalize_step_label(label)
        status_text = self._canonicalize_status_text(self._STATUS_LABELS.get(status, status))
        retry_text = f"，重試 {retry_count} 次" if retry_count else ""
        error_text = f"：{self._normalize_text(str(error))}" if error else ""
        return f"- {safe_label}：{status_text}{retry_text}{error_text}"

    def _canonicalize_step_label(self, label: str) -> str:
        normalized = self._normalize_text(label)
        alias_map = {
            "預覽 計畫": "預覽計畫",
            "選擇 技能": "選擇技能",
            "執行 技能": "執行技能",
            "驗證 結果": "驗證結果",
            "整理 輸出": "整理輸出",
        }
        return alias_map.get(normalized, normalized)

    def _canonicalize_status_text(self, text: str) -> str:
        normalized = self._normalize_text(text)
        alias_map = {
            "成 功": "成功",
            "失 敗": "失敗",
            "錯 誤": "錯誤",
            "略 過": "略過",
            "等 待中": "等待中",
            "執 行中": "執行中",
        }
        return alias_map.get(normalized, normalized)

    def _normalize_line(self, line: str) -> str:
        if not line:
            return ""
        normalized = self._normalize_text(line)
        normalized = re.sub(r"^\s*-\s*", "- ", normalized)
        normalized = re.sub(r"\s*：\s*", "：", normalized)
        normalized = re.sub(r"\s*，\s*", "，", normalized)
        normalized = re.sub(r"\s{2,}", " ", normalized)
        return normalized.strip()

    def _normalize_multiline_trace_text(self, text: str) -> str:
        if not text:
            return ""
        normalized = text.replace("\\r\\n", "\n").replace("\\n", "\n").replace("\\r", "\n")
        normalized = normalized.replace("\r\n", "\n").replace("\r", "\n")
        lines = []
        for raw_line in normalized.split("\n"):
            if not raw_line.strip():
                continue
            if raw_line.lstrip().startswith("-"):
                lines.append(self._normalize_line(raw_line))
            else:
                lines.append(self._normalize_text(raw_line))
        normalized = "\n".join(lines)
        normalized = re.sub(r"\n{2,}", "\n", normalized)
        return normalized.strip()

    def _normalize_text(self, text: str) -> str:
        if not text:
            return ""

        normalized = str(text)

        normalized = _ZERO_WIDTH_RE.sub("", normalized)
        normalized = normalized.replace("\u3000", " ").replace("\xa0", " ")
        normalized = normalized.replace("\r\n", "\n").replace("\r", "\n")

        # 只保留真正的換行，其他空白全部壓成單一空格
        normalized = re.sub(r"[^\S\n]+", " ", normalized)

        # 每行 trim
        normalized = "\n".join(line.strip() for line in normalized.split("\n"))

        # CJK 與 CJK 之間的空白去掉
        normalized = re.sub(rf"(?<=[{_CJK}]) +(?=[{_CJK}])", "", normalized)

        # 中文與標點之間空白去掉
        normalized = re.sub(rf"(?<=[{_CJK}]) +(?=[：，。！？])", "", normalized)
        normalized = re.sub(rf"(?<=[：，。！？]) +(?=[{_CJK}])", "", normalized)

        # dash 開頭規格化
        normalized = re.sub(r"(?m)^\s*-\s*", "- ", normalized)

        # 再做一次雙空白壓縮
        normalized = re.sub(r"[ ]{2,}", " ", normalized)

        return normalized.strip()
