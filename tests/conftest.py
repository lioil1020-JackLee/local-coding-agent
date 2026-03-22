from __future__ import annotations

import re
import shutil
import uuid
from pathlib import Path

import pytest


_REPO_ROOT = Path(__file__).resolve().parents[1]
_TEST_TMP_ROOT = _REPO_ROOT / "tmp_pytest_local"


def _safe_node_name(nodeid: str) -> str:
    name = re.sub(r"[^a-zA-Z0-9_-]+", "_", nodeid).strip("_")
    return (name[:48] or "test").lower()


@pytest.fixture
def tmp_path(request: pytest.FixtureRequest) -> Path:
    # 這個 fixture 避免部分 Windows 環境下 pytest 預設 tmp_path 權限不穩定的問題。
    _TEST_TMP_ROOT.mkdir(parents=True, exist_ok=True)
    path = _TEST_TMP_ROOT / f"{_safe_node_name(request.node.nodeid)}_{uuid.uuid4().hex[:8]}"
    path.mkdir(parents=True, exist_ok=False)
    try:
        yield path
    finally:
        shutil.rmtree(path, ignore_errors=True)
