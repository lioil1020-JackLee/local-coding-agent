from __future__ import annotations

import re


FORBIDDEN_CHAT_PATTERNS = [
    r"以下是修改",
    r"我幫你",
    r"修改說明",
    r"步驟如下",
    r"```",
    r"### ",
    r"^- ",
    r"^\d+\.",
]


def detect_chat_pollution(text: str) -> list[str]:
    """檢查內容是否混入聊天或說明文字。"""
    hits: list[str] = []

    for pattern in FORBIDDEN_CHAT_PATTERNS:
        if re.search(pattern, text, flags=re.MULTILINE):
            hits.append(pattern)

    return hits


def is_clean_code_text(text: str) -> bool:
    """判斷內容是否沒有明顯聊天污染。"""
    return len(detect_chat_pollution(text)) == 0