from __future__ import annotations

import re
from dataclasses import dataclass


@dataclass(frozen=True)
class PlainLanguageUnderstanding:
    suggested_intent: str | None = None
    force_plan_only: bool = False
    relative_path: str | None = None
    mode: str | None = None
    old_text: str | None = None
    content: str | None = None
    explanation: str = ""


class PlainLanguageUnderstandingService:
    """把白話需求轉成較穩定的執行提示。"""

    _ANALYZE_HINTS = ("先不要改", "先別改", "先分析", "先看懂", "幫我看懂", "這在做什麼", "先看看")
    _EDIT_HINTS = ("幫我改", "改一改", "調一下", "修一下", "幫我修改", "新增一段", "加上一行")
    _PATH_RE = re.compile(r"([^\s,，。;；:：\"'()（）]+/[^\s,，。;；:：\"'()（）]+\.[A-Za-z0-9_\-]+)")
    _FILENAME_RE = re.compile(r"([^\s,，。;；:：\"'()（）]+\.[A-Za-z0-9_\-]+)")
    _REPLACE_QUOTED_RE = re.compile(r"把[「\"](.+?)[」\"]改成[「\"](.+?)[」\"]")

    def interpret(self, text: str) -> PlainLanguageUnderstanding:
        raw = (text or "").strip()
        lowered = raw.lower()
        if not raw:
            return PlainLanguageUnderstanding(explanation="empty")

        relative_path = self._extract_relative_path(raw)
        replace_pair = self._extract_replace_pair(raw)

        if any(hint in raw for hint in self._ANALYZE_HINTS):
            return PlainLanguageUnderstanding(
                suggested_intent="analyze_repo",
                force_plan_only=False,
                relative_path=relative_path,
                explanation="analysis_first_phrase",
            )

        if replace_pair:
            old_text, content = replace_pair
            return PlainLanguageUnderstanding(
                suggested_intent="propose_edit",
                force_plan_only=True,
                relative_path=relative_path,
                mode="replace",
                old_text=old_text,
                content=content,
                explanation="replace_phrase_detected",
            )

        if any(hint in raw for hint in self._EDIT_HINTS):
            return PlainLanguageUnderstanding(
                suggested_intent="propose_edit",
                force_plan_only=True,
                relative_path=relative_path,
                mode="append",
                explanation="natural_edit_phrase",
            )

        # 英文白話補強
        if "first do not edit" in lowered or "read only" in lowered:
            return PlainLanguageUnderstanding(
                suggested_intent="analyze_repo",
                force_plan_only=False,
                relative_path=relative_path,
                explanation="english_read_only_phrase",
            )

        return PlainLanguageUnderstanding(relative_path=relative_path, explanation="neutral")

    def _extract_relative_path(self, text: str) -> str | None:
        found = self._PATH_RE.findall(text)
        if not found:
            found = self._FILENAME_RE.findall(text)
        if not found:
            if "readme" in text.lower():
                return "README.md"
            return None
        path = found[0].replace("\\", "/")
        if path.startswith("./"):
            path = path[2:]
        return path

    def _extract_replace_pair(self, text: str) -> tuple[str, str] | None:
        m = self._REPLACE_QUOTED_RE.search(text)
        if not m:
            return None
        old_text = m.group(1).strip()
        new_text = m.group(2).strip()
        if not old_text or not new_text:
            return None
        return old_text, new_text
