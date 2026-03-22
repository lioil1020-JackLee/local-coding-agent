from __future__ import annotations

from pathlib import Path
from typing import Iterable


class UnsafeEditContentError(ValueError):
    """表示待寫入內容疑似聊天說明文字，不允許直接寫入程式碼。"""


class ReadOnlyModeViolationError(ValueError):
    """表示在唯讀模式嘗試執行修改。"""


class SafeEditGuardService:
    """安全修改守門員：阻擋唯讀違規與聊天文字污染。"""

    CODE_LIKE_SUFFIXES = {
        ".py", ".js", ".ts", ".tsx", ".jsx", ".java", ".go", ".rs", ".c", ".cpp", ".cs", ".rb",
        ".php", ".swift", ".kt", ".scala", ".sh", ".bash", ".zsh", ".ps1", ".yml", ".yaml", ".toml",
        ".ini", ".cfg", ".conf", ".json",
    }

    CHAT_LEAKAGE_PATTERNS = (
        "<assistant>",
        "<user>",
        "以下是",
        "我已經",
        "你可以",
        "步驟如下",
        "建議你",
        "請注意",
        "```",
    )

    def ensure_not_read_only(self, *, read_only: bool) -> None:
        if read_only:
            raise ReadOnlyModeViolationError("目前為唯讀分析模式，禁止修改檔案。")

    def validate_edit_content(self, *, relative_path: str, content: str, mode: str = "append") -> None:
        suffix = Path(relative_path).suffix.lower()
        # 文件類型允許自然語言；程式/設定檔則強制防聊天文字污染。
        if suffix not in self.CODE_LIKE_SUFFIXES:
            return
        if not content or not content.strip():
            return

        lowered = content.lower()
        hits = [token for token in self.CHAT_LEAKAGE_PATTERNS if token.lower() in lowered]
        bullet_like = any(line.strip().startswith("- ") for line in content.splitlines())

        if hits or bullet_like:
            reason = ", ".join(hits) if hits else "bullet_list_detected"
            raise UnsafeEditContentError(f"偵測到疑似聊天說明文字，已阻擋寫入程式碼（{reason}）。")

        # replace 模式通常應是精準內容，若整段幾乎都是中文自然語句也視為風險。
        if mode == "replace":
            cjk_count = sum(1 for ch in content if "\u4e00" <= ch <= "\u9fff")
            symbol_count = sum(1 for ch in content if ch in "{}[]()=;:.,_<>+-*/'\"")
            if cjk_count >= 20 and symbol_count <= 2:
                raise UnsafeEditContentError("replace 內容疑似自然語言說明，已阻擋寫入程式碼。")

    def validate_operations(self, operations: Iterable[dict]) -> None:
        for op in operations:
            if not isinstance(op, dict):
                continue
            self.validate_edit_content(
                relative_path=str(op.get("relative_path") or ""),
                content=str(op.get("content") or ""),
                mode=str(op.get("mode") or "append"),
            )

