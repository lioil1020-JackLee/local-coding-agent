from __future__ import annotations

from pathlib import Path

from repo_guardian_mcp.models import RepoOverviewResult
from repo_guardian_mcp.utils.paths import list_files_recursive


class RepoScanService:
    """
    負責掃描整個 repo。
    """

    def __init__(self, workspace_root: Path):
        self.workspace_root = workspace_root

    def scan(self) -> RepoOverviewResult:
        """
        掃描 repo 結構。
        """

        detected_languages: set[str] = set()
        likely_entrypoints: list[str] = []
        likely_test_commands: list[str] = []
        likely_build_commands: list[str] = []

        # 掃描 Python 檔案
        py_files = list_files_recursive(self.workspace_root, (".py",))

        if py_files:
            detected_languages.add("Python")

        # 找常見入口
        for file in py_files:
            name = file.name

            if name in (
                "main.py",
                "app.py",
                "server.py",
                "manage.py",
                "__main__.py",
            ):
                likely_entrypoints.append(str(file.relative_to(self.workspace_root)))

        # 簡單推測 test / build
        if (self.workspace_root / "pyproject.toml").exists():
            likely_test_commands.append("pytest")
            likely_build_commands.append("python -m build")

        summary = "掃描完成"

        return RepoOverviewResult(
            project_root=str(self.workspace_root),
            detected_languages=sorted(detected_languages),
            likely_entrypoints=likely_entrypoints,
            likely_test_commands=likely_test_commands,
            likely_build_commands=likely_build_commands,
            summary=summary,
        )