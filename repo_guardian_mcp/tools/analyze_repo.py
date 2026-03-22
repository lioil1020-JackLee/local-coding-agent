from __future__ import annotations

"""
analyze_repo 工具

此工具提供專案總覽，用於幫助使用者快速了解專案結構和重點檔案。它僅進行
唯讀分析，依賴 ``RepoScanService`` 掃描專案，並回傳容易理解的摘要資訊。
"""

import ast
from pathlib import Path
from typing import Any

from repo_guardian_mcp.services.repo_scan_service import RepoScanService


def _read_text_with_fallback(path: Path) -> str:
    data = path.read_bytes()
    for encoding in ("utf-8", "utf-8-sig", "utf-16", "utf-16-le", "utf-16-be", "cp950"):
        try:
            return data.decode(encoding)
        except UnicodeDecodeError:
            continue
    return data.decode("utf-8", errors="replace")


def _build_python_evidence(
    root: Path,
    service: RepoScanService,
    *,
    read_all_python: bool = False,
    sample_limit: int = 24,
) -> dict[str, Any]:
    py_files = service.iter_files(root, suffixes=(".py",))
    evidence: list[dict[str, Any]] = []
    scanned = 0
    parse_error_count = 0
    total_line_count = 0
    total_function_count = 0
    total_class_count = 0

    scan_targets = py_files if read_all_python else py_files[:sample_limit]
    for file_path in scan_targets:
        rel = file_path.relative_to(root).as_posix()
        try:
            text = _read_text_with_fallback(file_path)
        except OSError:
            continue
        scanned += 1

        line_count = len(text.splitlines())
        total_line_count += line_count
        has_main_guard = "__name__ == \"__main__\"" in text or "__name__ == '__main__'" in text
        classes: list[str] = []
        functions: list[str] = []
        module_doc = ""

        try:
            tree = ast.parse(text)
            doc = ast.get_docstring(tree) or ""
            module_doc = doc.strip().splitlines()[0] if doc.strip() else ""
            for node in tree.body:
                if isinstance(node, ast.ClassDef):
                    classes.append(node.name)
                elif isinstance(node, ast.FunctionDef):
                    functions.append(node.name)
        except SyntaxError:
            module_doc = ""
            parse_error_count += 1

        total_function_count += len(functions)
        total_class_count += len(classes)

        evidence.append(
            {
                "path": rel,
                "line_count": line_count,
                "has_main_guard": has_main_guard,
                "top_level_classes": classes[:5],
                "top_level_functions": functions[:8],
                "module_doc": module_doc[:120],
            }
        )

    return {
        "python_files_total": len(py_files),
        "python_scan_mode": "all" if read_all_python else "sample",
        "python_files_scanned_count": scanned,
        "python_files_sampled": len(evidence),
        "python_files_unscanned_count": max(0, len(py_files) - scanned),
        "python_parse_error_count": parse_error_count,
        "python_total_line_count": total_line_count,
        "python_total_top_level_functions": total_function_count,
        "python_total_top_level_classes": total_class_count,
        "all_python_read": bool(read_all_python and scanned == len(py_files)),
        "python_evidence": evidence,
    }


def _estimate_completion(*, root: Path, important_files: list[str], entrypoints: list[str], python_files_total: int) -> dict[str, Any]:
    has_readme = "README.md" in important_files
    has_project_config = any(name in important_files for name in ("pyproject.toml", "requirements.txt"))
    has_entrypoint = bool(entrypoints)
    has_tests = (root / "tests").exists()
    has_docs = (root / "docs").exists()
    has_ci = (root / ".github" / "workflows").exists()

    score = 0
    if python_files_total > 0:
        score += 20
    if has_readme:
        score += 15
    if has_project_config:
        score += 15
    if has_entrypoint:
        score += 20
    if has_tests:
        score += 15
    if has_docs:
        score += 10
    if has_ci:
        score += 5

    score = max(0, min(100, score))
    if score >= 80:
        level = "成熟度偏高"
    elif score >= 60:
        level = "可用但仍在擴充"
    elif score >= 40:
        level = "基礎雛型"
    else:
        level = "早期階段"

    return {
        "score": score,
        "level": level,
        "is_heuristic": True,
        "signals": {
            "has_readme": has_readme,
            "has_project_config": has_project_config,
            "has_entrypoint": has_entrypoint,
            "has_tests": has_tests,
            "has_docs": has_docs,
            "has_ci": has_ci,
        },
    }


def analyze_repo_tool(
    repo_root: str,
    read_all_python: bool = False,
    sample_limit: int = 24,
) -> dict:
    """
    提供專案總覽工具，給予資料整理後的摘要。

    參數：
        repo_root (str): 專案根目錄。

    回傳：
        dict: 包含 ``ok``、``project_name``、``top_level_directories`` 等資料的字典。
    """
    root = Path(repo_root).resolve()
    service = RepoScanService()
    summary = service.summarize_repo(root)
    safe_sample_limit = max(1, min(int(sample_limit or 24), 200))
    python_insights = _build_python_evidence(
        root,
        service,
        read_all_python=bool(read_all_python),
        sample_limit=safe_sample_limit,
    )

    focus_files: list[str] = []
    for rel in summary.important_files + summary.entrypoints:
        if rel not in focus_files:
            focus_files.append(rel)

    completion_estimate = _estimate_completion(
        root=root,
        important_files=summary.important_files,
        entrypoints=summary.entrypoints,
        python_files_total=int(python_insights["python_files_total"]),
    )

    return {
        "ok": True,
        "repo_root": str(root),
        "project_name": root.name,
        "top_level_directories": summary.top_level_directories,
        "total_files": summary.total_files,
        "total_python_files": summary.total_python_files,
        "important_files": summary.important_files,
        "entrypoints": summary.entrypoints,
        "focus_files": focus_files[:12],
        **python_insights,
        "completion_estimate": completion_estimate,
        "summary": {
            "project_name": root.name,
            "start_here": focus_files[:5],
            "notes": [
                (
                    "此結果已逐一讀取全部 Python 程式碼。"
                    if read_all_python
                    else "此結果已實際抽樣 Python 程式碼，不只看 README。"
                ),
                "completion_estimate 為啟發式估算，請搭配程式碼證據一起解讀。",
            ],
        },
    }


# 保留別名，讓既有程式或 MCP 註冊引用不需一起改名
analyze_repo = analyze_repo_tool
