from __future__ import annotations

import shutil
import subprocess
from pathlib import Path


class GitSessionMaintenanceService:
    """清理 session 產生的 git / sandbox 殘留。

    目標：
    - 清除 agent_runtime/sandbox_workspaces/<session_id>
    - 清除 agent_runtime/sandbox_worktrees/<session_id>
    - 嘗試刪除 rg/session-* branch
    - 執行 git worktree prune，避免 VS Code 持續看到大量無效 worktree
    """

    def __init__(self, repo_root: str | Path) -> None:
        self.repo_root = Path(repo_root).resolve()
        self.runtime_root = self.repo_root / 'agent_runtime'
        self.git_dir = self.repo_root / '.git'

    def cleanup_session_artifacts(
        self,
        *,
        session_id: str,
        sandbox_path: str | Path | None = None,
        branch_name: str | None = None,
    ) -> dict[str, object]:
        removed_paths: list[str] = []
        removed_branch = False
        prune_attempted = False

        explicit_sandbox = Path(sandbox_path).resolve() if sandbox_path else None
        for candidate in self._candidate_paths(session_id=session_id, explicit_sandbox=explicit_sandbox):
            if self._remove_path(candidate):
                removed_paths.append(str(candidate))

        if branch_name:
            removed_branch = self._delete_branch(branch_name)

        prune_attempted = self.prune_worktrees()

        return {
            'removed_paths': removed_paths,
            'removed_branch': removed_branch,
            'prune_attempted': prune_attempted,
        }

    def prune_worktrees(self) -> bool:
        if not self.git_dir.exists():
            return False
        try:
            subprocess.run(
                ['git', 'worktree', 'prune'],
                cwd=self.repo_root,
                capture_output=True,
                text=True,
                timeout=30,
                check=False,
            )
            return True
        except Exception:
            return False

    def _candidate_paths(self, *, session_id: str, explicit_sandbox: Path | None) -> list[Path]:
        candidates: list[Path] = []
        if explicit_sandbox is not None:
            candidates.append(explicit_sandbox)
        candidates.append(self.runtime_root / 'sandbox_workspaces' / session_id)
        candidates.append(self.runtime_root / 'sandbox_worktrees' / session_id)
        return self._dedupe_paths(candidates)

    @staticmethod
    def _dedupe_paths(paths: list[Path]) -> list[Path]:
        seen: set[str] = set()
        result: list[Path] = []
        for path in paths:
            key = str(path)
            if key in seen:
                continue
            seen.add(key)
            result.append(path)
        return result

    def _delete_branch(self, branch_name: str) -> bool:
        try:
            result = subprocess.run(
                ['git', 'branch', '-D', branch_name],
                cwd=self.repo_root,
                capture_output=True,
                text=True,
                timeout=30,
                check=False,
            )
            if result.returncode == 0:
                return True
        except Exception:
            pass

        # fallback: 刪 refs/heads/<branch_name>
        ref_path = self.git_dir / 'refs' / 'heads' / Path(branch_name)
        try:
            if ref_path.exists():
                ref_path.unlink()
                self._prune_empty_parents(ref_path.parent, stop=self.git_dir / 'refs' / 'heads')
                return True
        except Exception:
            return False
        return False

    def _prune_empty_parents(self, start: Path, stop: Path) -> None:
        current = start
        stop = stop.resolve()
        while True:
            try:
                if current.resolve() == stop:
                    break
            except Exception:
                break
            try:
                current.rmdir()
            except OSError:
                break
            current = current.parent

    @staticmethod
    def _remove_path(path: Path) -> bool:
        if not path.exists():
            return False
        try:
            if path.is_file() or path.is_symlink():
                path.unlink(missing_ok=True)
                return True
            shutil.rmtree(path, ignore_errors=True)
            return not path.exists()
        except Exception:
            return False
