from __future__ import annotations

"""
symbol_service

提供搜尋符號與建立簡易符號索引的服務。主要用於搜尋程式碼片段
以及列出 Python 檔案中的類別與函式定義位置。
"""

import ast
from pathlib import Path

from repo_guardian_mcp.utils.file_utils import read_file_safe
from repo_guardian_mcp.utils.paths import list_files_recursive


class SymbolService:
    """負責搜尋符號與建立 Python symbol index。"""

    def __init__(self, workspace_root: Path):
        self.workspace_root = workspace_root

    def search(self, query: str, extensions: tuple[str, ...] = (".py",)) -> list[dict]:
        """在指定擴充名的檔案內搜尋包含 query 的行。

        回傳的每個結果包含檔案相對路徑、行號以及行文字。
        """
        results: list[dict] = []
        files = list_files_recursive(self.workspace_root, extensions)
        for file in files:
            try:
                content = read_file_safe(file)
            except Exception:
                continue
            lines = content.splitlines()
            for index, line in enumerate(lines, start=1):
                if query.lower() in line.lower():
                    results.append(
                        {
                            "file_path": str(file.relative_to(self.workspace_root)),
                            "line_number": index,
                            "line_text": line.strip(),
                        }
                    )
        return results

    def build_symbol_index(self) -> list[dict]:
        """建立 Python 檔案的類別與函式索引。"""
        results: list[dict] = []
        py_files = list_files_recursive(self.workspace_root, (".py",))
        for file in py_files:
            try:
                content = read_file_safe(file)
                tree = ast.parse(content)
            except Exception:
                continue
            relative_path = str(file.relative_to(self.workspace_root))
            for node in ast.walk(tree):
                if isinstance(node, ast.ClassDef):
                    results.append(
                        {
                            "symbol_type": "class",
                            "name": node.name,
                            "file_path": relative_path,
                            "line_number": node.lineno,
                        }
                    )
                elif isinstance(node, ast.FunctionDef):
                    results.append(
                        {
                            "symbol_type": "function",
                            "name": node.name,
                            "file_path": relative_path,
                            "line_number": node.lineno,
                        }
                    )
                elif isinstance(node, ast.AsyncFunctionDef):
                    results.append(
                        {
                            "symbol_type": "async_function",
                            "name": node.name,
                            "file_path": relative_path,
                            "line_number": node.lineno,
                        }
                    )
        return sorted(results, key=lambda item: (item["file_path"], item["line_number"], item["name"]))