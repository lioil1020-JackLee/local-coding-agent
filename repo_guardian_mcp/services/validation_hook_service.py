from __future__ import annotations

from typing import Any


def run_validation_hook(diff_text: str) -> dict[str, Any]:
    """
    最小可用版 validation hook

    規則：
    - 有 diff -> pass
    - 沒 diff -> fail
    """

    changed = bool(diff_text and diff_text.strip())

    if changed:
        return {
            "status": "pass",
            "passed": True,
            "checks": [
                {
                    "name": "diff_present",
                    "status": "pass",
                    "message": "Diff detected in sandbox session.",
                }
            ],
            "summary": "Validation passed: diff detected.",
        }

    return {
        "status": "fail",
        "passed": False,
        "checks": [
            {
                "name": "diff_present",
                "status": "fail",
                "message": "No diff detected in sandbox session.",
            }
        ],
        "summary": "Validation failed: no diff detected.",
    }