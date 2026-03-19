from __future__ import annotations

import json

from repo_guardian_mcp.cli import main
from repo_guardian_mcp.tools.create_task_session import create_task_session


def test_cli_diff_handles_non_utf8_file(tmp_path, capsys):
    (tmp_path / "README.md").write_text("before\n", encoding="utf-8")
    created = create_task_session(str(tmp_path), create_workspace=True)
    session_id = created["session_id"]

    sandbox_dir = tmp_path / "agent_runtime" / "sandbox_workspaces" / session_id
    binary_file = sandbox_dir / "binary.bin"
    binary_file.write_bytes(b"\xff\xfe\x00\xbabinary")

    code = main(["diff", str(tmp_path), session_id])
    captured = capsys.readouterr()

    assert code == 0
    data = json.loads(captured.out)
    assert data["ok"] is True
    assert "binary.bin" in data["changed_files"]
