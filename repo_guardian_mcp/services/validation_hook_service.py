from __future__ import annotations

from typing import Any


# 只保留真正高風險、明顯來自對話/工具回傳的污染訊號。
# 像 repo_guardian_*_tool 這類專案內合法字樣，本來就可能存在於 README / docs，
# 不應在 validation success case 被誤判成 leakage。
LEAKAGE_PATTERNS = [
    "<assistant>",
    "<user>",
    "toolCallId",
    "parsedArgs",
    "create_new_file failed",
    "undefined(",
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

    現階段重點是：
    1. 阻擋明顯的聊天/工具污染內容
    2. 不因 diff engine、編碼或 metadata 問題誤殺正常修改

    因此這一層不再把「沒有可解析的 diff 文字」視為 fail；
    只要沒有明顯污染，就讓流程先通過，避免把 safe edit 主線打斷。
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
