from __future__ import annotations

import subprocess
from pathlib import Path


def run_command(
    command: list[str],
    cwd: Path | None = None,
) -> dict[str, str | int | bool]:
    """執行系統指令並回傳結果。"""

    result = subprocess.run(
        command,
        cwd=cwd,
        capture_output=True,
        text=True,
    )

    return {
        "command": " ".join(command),
        "returncode": result.returncode,
        "stdout": result.stdout,
        "stderr": result.stderr,
        "success": result.returncode == 0,
    }