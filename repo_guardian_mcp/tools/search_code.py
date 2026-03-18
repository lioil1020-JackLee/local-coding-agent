from __future__ import annotations

"""
search_code 工具

提供在專案根目錄下搜尋程式碼的能力。使用 SymbolService 來
搜尋包含指定關鍵字的行。回傳包含檔案路徑、行號與行內容的列表。

範例：

```
from pathlib import Path
from repo_guardian_mcp.tools.search_code import search_code
print(search_code(Path("/path/to/repo"), "TODO"))
```
"""

from pathlib import Path

from repo_guardian_mcp.services.symbol_service import SymbolService


def search_code(workspace_root: Path, query: str) -> list[dict]:
    """在 workspace_root 中搜尋包含 query 的程式碼行。"""
    service = SymbolService(workspace_root)
    return service.search(query)