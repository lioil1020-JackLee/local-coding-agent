from __future__ import annotations

from pathlib import Path
from typing import Any


def _find_existing(paths: list[Path]) -> list[str]:
    return [str(p) for p in paths if p.exists()]


def repo_overview(repo_root: str) -> dict[str, Any]:
    root = Path(repo_root).resolve()

    important_files = _find_existing(
        [
            root / "README.md",
            root / "pyproject.toml",
            root / ".env.example",
            root / "CHANGELOG.md",
            root / "CONTRIBUTING.md",
        ]
    )

    important_dirs = [str(p) for p in root.iterdir() if p.is_dir() and not p.name.startswith(".")]
    important_dirs.sort()

    return {
        "ok": True,
        "repo_root": str(root),
        "project_name": root.name,
        "important_files": important_files,
        "important_dirs": important_dirs,
    }


def get_repo_overview(repo_root: str) -> dict[str, Any]:
    return repo_overview(repo_root)


def run(repo_root: str) -> dict[str, Any]:
    return repo_overview(repo_root)