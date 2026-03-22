from pathlib import Path

import pytest

from repo_guardian_mcp.services.safe_edit_guard_service import (
    ReadOnlyModeViolationError,
    SafeEditGuardService,
    UnsafeEditContentError,
)
from repo_guardian_mcp.services.sandbox_edit_service import apply_text_edit
from repo_guardian_mcp.services.task_orchestrator import TaskOrchestrator


def test_guard_blocks_chat_text_for_code_file(tmp_path: Path):
    sandbox = tmp_path / "sandbox"
    sandbox.mkdir()
    target = sandbox / "main.py"
    target.write_text("print('ok')\n", encoding="utf-8")

    with pytest.raises(UnsafeEditContentError):
        apply_text_edit(
            sandbox_path=sandbox,
            relative_path="main.py",
            content="以下是我幫你整理的步驟如下：\n- 第一點\n- 第二點",
            mode="append",
        )


def test_guard_allows_natural_language_for_markdown(tmp_path: Path):
    sandbox = tmp_path / "sandbox"
    sandbox.mkdir()
    target = sandbox / "README.md"
    target.write_text("demo\n", encoding="utf-8")

    edited = apply_text_edit(
        sandbox_path=sandbox,
        relative_path="README.md",
        content="以下是說明文件更新內容",
        mode="append",
    )
    assert Path(edited).exists()


def test_read_only_lock_blocks_edit():
    orchestrator = TaskOrchestrator()
    result = orchestrator.run(
        repo_root=".",
        task_type="edit",
        relative_path="README.md",
        content="x",
        metadata={"read_only": True},
    )
    assert result["ok"] is False
    assert "唯讀" in result["error"]


def test_guard_service_read_only_violation():
    guard = SafeEditGuardService()
    with pytest.raises(ReadOnlyModeViolationError):
        guard.ensure_not_read_only(read_only=True)

