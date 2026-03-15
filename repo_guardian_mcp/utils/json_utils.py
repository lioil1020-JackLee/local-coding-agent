from __future__ import annotations

import json
from pathlib import Path
from typing import Any


def load_json_file(path: Path) -> dict[str, Any]:
    """讀取 JSON 檔案。"""
    if not path.exists():
        raise FileNotFoundError(f"JSON 檔案不存在: {path}")

    with path.open("r", encoding="utf-8") as f:
        data = json.load(f)

    if not isinstance(data, dict):
        raise ValueError(f"JSON 內容不是物件格式: {path}")

    return data


def save_json_file(path: Path, data: dict[str, Any]) -> None:
    """儲存 JSON 檔案。"""
    path.parent.mkdir(parents=True, exist_ok=True)

    with path.open("w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)