from __future__ import annotations

import py_compile
from pathlib import Path
from typing import Any

from repo_guardian_mcp.utils.git_utils import get_diff_against_commit


# 舊測試仍在使用這個函式，所以保留相容介面。
def validate_patch(patch: dict[str, Any]) -> dict[str, Any]:
    return {"valid": True, "issues": []}


class ValidationService:
    """針對 session 做最基本但可用的驗證。"""

    def __init__(self, repo_root: str | Path) -> None:
        self.repo_root = Path(repo_root).resolve()
        self.sessions_root = self.repo_root / "agent_runtime" / "sessions"

    def validate_session(self, session_id: str) -> dict[str, Any]:
        if not session_id or not session_id.strip():
            return {
                "ok": False,
                "error": "session_id 不能為空",
            }

        session_file = self.sessions_root / f"{session_id}.json"
        if not session_file.exists():
            return {
                "ok": False,
                "error": f"找不到 session 檔案: {session_file}",
                "session_id": session_id,
            }

        import json

        data = json.loads(session_file.read_text(encoding="utf-8"))
        sandbox_path = Path(data.get("sandbox_path", "")).resolve()
        base_commit = data.get("base_commit")
        edited_files = data.get("edited_files", [])

        checks: list[dict[str, Any]] = []

        checks.append({
            "name": "session_file_exists",
            "passed": True,
            "detail": str(session_file),
        })

        sandbox_exists = sandbox_path.exists()
        checks.append({
            "name": "sandbox_exists",
            "passed": sandbox_exists,
            "detail": str(sandbox_path),
        })

        diff_text = ""
        diff_ok = False
        if sandbox_exists and base_commit:
            try:
                diff_text = get_diff_against_commit(sandbox_path, base_commit)
                diff_ok = isinstance(diff_text, str)
            except Exception as exc:
                checks.append({
                    "name": "diff_generation",
                    "passed": False,
                    "detail": str(exc),
                })
            else:
                checks.append({
                    "name": "diff_generation",
                    "passed": True,
                    "detail": "diff 產生成功",
                })
        else:
            checks.append({
                "name": "diff_generation",
                "passed": False,
                "detail": "sandbox 或 base_commit 不可用",
            })

        compile_results: list[dict[str, Any]] = []
        if sandbox_exists:
            for edited_file in edited_files:
                file_path = Path(edited_file)
                if file_path.suffix != ".py":
                    continue
                try:
                    py_compile.compile(str(file_path), doraise=True)
                except Exception as exc:
                    compile_results.append({
                        "path": str(file_path),
                        "passed": False,
                        "detail": str(exc),
                    })
                else:
                    compile_results.append({
                        "path": str(file_path),
                        "passed": True,
                        "detail": "python 編譯檢查通過",
                    })

        compile_passed = all(item["passed"] for item in compile_results) if compile_results else True
        checks.append({
            "name": "python_compile",
            "passed": compile_passed,
            "detail": f"檢查 {len(compile_results)} 個 Python 檔案",
        })

        passed = all(item["passed"] for item in checks)

        summary = "驗證通過" if passed else "驗證未通過"
        return {
            "ok": True,
            "session_id": session_id,
            "passed": passed,
            "summary": summary,
            "checks": checks,
            "compile_results": compile_results,
            "diff_preview": diff_text[:4000],
        }


def validate_session(repo_root: str, session_id: str) -> dict[str, Any]:
    return ValidationService(repo_root).validate_session(session_id)
