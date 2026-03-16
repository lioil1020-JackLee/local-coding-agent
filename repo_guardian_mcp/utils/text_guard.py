from __future__ import annotations


def is_safe_text(text: str) -> bool:
    """
    最小版 text guard

    目前只做簡單檢查：
    - 不能是空字串
    """

    if text is None:
        return False

    if not text.strip():
        return False

    return True