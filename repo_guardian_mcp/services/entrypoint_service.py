from __future__ import annotations

from pathlib import Path

from repo_guardian_mcp.utils.paths import list_files_recursive


class EntrypointService:
    """
    負責尋找 repo 的可能入口點。
    """

    COMMON_ENTRYPOINTS = (
        "main.py",
        "app.py",
        "server.py",
        "manage.py",
        "__main__.py",
    )

    def __init__(self, workspace_root: Path):
        self.workspace_root = workspace_root

    def find_entrypoints(self) -> list[str]:
        """
        搜尋 repo 中可能的入口檔。
        """

        results: list[str] = []

        py_files = list_files_recursive(self.workspace_root, (".py",))

        for file in py_files:
            if file.name in self.COMMON_ENTRYPOINTS:
                results.append(str(file.relative_to(self.workspace_root)))

        return sorted(results)