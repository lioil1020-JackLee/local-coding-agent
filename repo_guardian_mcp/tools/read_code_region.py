from __future__ import annotations

"""
read_code_region 工具

讀取指定檔案的特定行數範圍，回傳檔案路徑、起迄行與內容。

此工具會確保要求的檔案位於工作目錄之下，避免路徑穿越攻擊。
"""

from pathlib import Path

from repo_guardian_mcp.utils.file_utils import read_file_region


def read_code_region(
    workspace_root: Path,
    file_path: str,
    start_line: int,
    end_line: int,
) -> dict:
    """讀取 workspace_root 中某檔案的部分程式碼區段。"""
    if start_line <= 0:
        raise ValueError("start_line 必須大於 0")
    if end_line < start_line:
        raise ValueError("end_line 不可小於 start_line")
    target_path = (workspace_root / file_path).resolve()
    workspace_root = workspace_root.resolve()
    # 確保路徑在 workspace 內部
    if workspace_root not in target_path.parents and target_path != workspace_root:
        raise ValueError("file_path 超出 workspace 範圍")
    content = read_file_region(target_path, start_line, end_line)
    return {
        "file_path": file_path,
        "start_line": start_line,
        "end_line": end_line,
        "content": content,
    }