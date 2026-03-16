from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Iterable

# 分析 repo 時預設要忽略的資料夾。
# 這裡特別排除 agent_runtime，避免把 sandbox worktree、session 檔、log 當成真正專案內容。
DEFAULT_IGNORED_DIR_NAMES: set[str] = {
    ".git",
    ".hg",
    ".svn",
    ".venv",
    "venv",
    "node_modules",
    "__pycache__",
    ".pytest_cache",
    ".mypy_cache",
    ".ruff_cache",
    "dist",
    "build",
    "agent_runtime",
}

# 常見的專案入口點候選。
ENTRYPOINT_CANDIDATES: tuple[str, ...] = (
    "main.py",
    "app.py",
    "server.py",
    "manage.py",
    "cli.py",
    "run.py",
    "__main__.py",
)

# 這些檔案通常很適合拿來當 repo 導覽重點。
IMPORTANT_FILE_CANDIDATES: tuple[str, ...] = (
    "README.md",
    "pyproject.toml",
    "requirements.txt",
    "package.json",
    "Dockerfile",
    "docker-compose.yml",
)


@dataclass(slots=True)
class RepoScanSummary:
    repo_root: str
    total_files: int
    total_python_files: int
    top_level_directories: list[str]
    important_files: list[str]
    entrypoints: list[str]


class RepoScanService:
    """提供唯讀的 repo 掃描能力。

    這個 service 的重點不是做很複雜的語意分析，
    而是先穩定地把「真正專案內容」掃出來。
    """

    def __init__(self, ignored_dir_names: Iterable[str] | None = None) -> None:
        ignored = set(DEFAULT_IGNORED_DIR_NAMES)
        if ignored_dir_names:
            ignored.update(ignored_dir_names)
        self.ignored_dir_names = ignored

    def _should_skip_dir(self, path: Path) -> bool:
        return path.name in self.ignored_dir_names

    def iter_files(self, repo_root: str | Path, suffixes: tuple[str, ...] | None = None) -> list[Path]:
        root = Path(repo_root).resolve()
        files: list[Path] = []

        for path in root.rglob("*"):
            if path.is_dir() and self._should_skip_dir(path):
                continue
            if not path.is_file():
                continue
            if any(part in self.ignored_dir_names for part in path.relative_to(root).parts):
                continue
            if suffixes and path.suffix.lower() not in suffixes:
                continue
            files.append(path)

        return sorted(files)

    def get_top_level_directories(self, repo_root: str | Path) -> list[str]:
        root = Path(repo_root).resolve()
        directories: list[str] = []
        for child in sorted(root.iterdir()):
            if child.is_dir() and not self._should_skip_dir(child):
                directories.append(child.name)
        return directories

    def get_important_files(self, repo_root: str | Path, limit: int = 12) -> list[str]:
        root = Path(repo_root).resolve()
        results: list[str] = []

        for name in IMPORTANT_FILE_CANDIDATES:
            path = root / name
            if path.exists() and path.is_file():
                results.append(path.relative_to(root).as_posix())

        # 補一些常見設定檔，讓使用者比較容易知道從哪裡看起。
        for pattern in ("continue/**/*.md", "docs/*.md", "repo_guardian_mcp/server.py"):
            for path in sorted(root.glob(pattern)):
                if path.is_file():
                    rel = path.relative_to(root).as_posix()
                    if rel not in results:
                        results.append(rel)
                if len(results) >= limit:
                    return results[:limit]

        return results[:limit]

    def find_entrypoints(self, repo_root: str | Path, limit: int = 12) -> list[str]:
        root = Path(repo_root).resolve()
        entrypoints: list[str] = []

        for file_path in self.iter_files(root, suffixes=(".py",)):
            rel = file_path.relative_to(root).as_posix()
            name = file_path.name
            if name in ENTRYPOINT_CANDIDATES:
                entrypoints.append(rel)
                continue
            if rel.startswith("repo_guardian_mcp/tools/"):
                continue
            if rel.startswith("tests/"):
                continue
            if rel.endswith("/server.py") or rel.endswith("/main.py"):
                entrypoints.append(rel)

        return entrypoints[:limit]

    def summarize_repo(self, repo_root: str | Path) -> RepoScanSummary:
        root = Path(repo_root).resolve()
        all_files = self.iter_files(root)
        py_files = self.iter_files(root, suffixes=(".py",))

        return RepoScanSummary(
            repo_root=str(root),
            total_files=len(all_files),
            total_python_files=len(py_files),
            top_level_directories=self.get_top_level_directories(root),
            important_files=self.get_important_files(root),
            entrypoints=self.find_entrypoints(root),
        )
