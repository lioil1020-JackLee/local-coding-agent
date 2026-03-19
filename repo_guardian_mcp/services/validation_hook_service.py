from __future__ import annotations

"""
validation_hook_service 提供最小驗證鉤子，檢查 diff 中是否有明顯的聊天或工具漏出。

這層不會阻擋沒有 diff 的情況，只檢查新增行是否含敏感字串。
"""

from typing import Any

LEAKAGE_PATTERNS = [
    "<assistant>",
    "<user>",
    "toolCallId",
    "parsedArgs",
    "create_new_file failed",
    "undefined(",
]

BANNED_PATTERNS = [
    "TODO",
    "FIXME",
]


def _extract_added_lines(diff_text: str) -> list[str]:
    """只檢查 diff 新增內容，避免被既有 repo 文字誤傷。"""
    added_lines: list[str] = []
    for line in (diff_text or "").splitlines():
        if not line.startswith("+"):
            continue
        if line.startswith("+++"):
            continue
        added_lines.append(line[1:])
    return added_lines


def run_validation_hook(diff_text: str) -> dict[str, Any]:
    """
    正式版最小 validation hook。

    現階段重點：
    1. 阻擋明顯聊天/工具污染
    2. 阻擋 TODO / FIXME 這類未完成標記
    3. 不因 benign 的長行、編碼替換字元或 diff engine 細節誤殺正常修改

    說明：
    先前 line_length_guard 直接把長行視為 fail，會導致：
    - README append 這類正常文件修改被誤判
    - replace 測試中的較長字串替換被誤判
    - session status 變成 validation_failed

    現在改為：
    - 長行只作為 warning/pass，不阻擋 safe-edit 主線
    """

    checks: list[dict[str, str]] = []
    has_diff_text = bool(diff_text and diff_text.strip())
    added_lines = _extract_added_lines(diff_text)
    added_text = "\n".join(added_lines)

    if has_diff_text:
        checks.append(
            {
                "name": "diff_present",
                "status": "pass",
                "message": "Diff detected in sandbox session.",
            }
        )
    else:
        checks.append(
            {
                "name": "diff_present",
                "status": "pass",
                "message": "No textual diff detected; content validation skipped for this session.",
            }
        )

    leakage_found = [pattern for pattern in LEAKAGE_PATTERNS if pattern in added_text]
    if leakage_found:
        checks.append(
            {
                "name": "chat_leakage_guard",
                "status": "fail",
                "message": f"Detected suspicious chat text leakage: {', '.join(leakage_found)}",
            }
        )
    else:
        checks.append(
            {
                "name": "chat_leakage_guard",
                "status": "pass",
                "message": "No obvious chat text leakage detected in added lines.",
            }
        )

    banned_found = [pattern for pattern in BANNED_PATTERNS if pattern in added_text]
    if banned_found:
        checks.append(
            {
                "name": "banned_words_guard",
                "status": "fail",
                "message": f"Detected banned patterns: {', '.join(banned_found)}",
            }
        )
    else:
        checks.append(
            {
                "name": "banned_words_guard",
                "status": "pass",
                "message": "No banned keywords found in added lines.",
            }
        )

    long_lines = [line for line in added_lines if len(line) > 120]
    if long_lines:
        checks.append(
            {
                "name": "line_length_guard",
                "status": "pass",
                "message": f"Found {len(long_lines)} long added lines (>120 chars), but treated as warning.",
            }
        )
    else:
        checks.append(
            {
                "name": "line_length_guard",
                "status": "pass",
                "message": "All added lines are within acceptable length.",
            }
        )

    passed = all(check["status"] == "pass" for check in checks)
    status = "pass" if passed else "fail"
    summary = "Validation passed." if passed else "Validation failed."

    return {
        "status": status,
        "passed": passed,
        "checks": checks,
        "summary": summary,
        "has_diff_text": has_diff_text,
        "added_lines_checked": len(added_lines),
    }
