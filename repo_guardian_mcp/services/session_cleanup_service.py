from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from enum import Enum
from pathlib import Path
from typing import Any, Iterable, Protocol
import json
import shutil


class SessionStatus(str, Enum):
    CREATED = "created"
    ACTIVE = "active"
    VALIDATING = "validating"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    ROLLED_BACK = "rolled_back"
    ABANDONED = "abandoned"
    CLEANED = "cleaned"


@dataclass(slots=True)
class SessionRecord:
    session_id: str
    status: str
    pinned: bool = False
    created_at: datetime | None = None
    last_accessed_at: datetime | None = None
    expires_at: datetime | None = None
    workspace_path: Path | None = None
    metadata_path: Path | None = None
    extra: dict[str, Any] = field(default_factory=dict)


@dataclass(slots=True)
class CleanupDecision:
    session_id: str
    reason: str
    reclaimed_bytes: int


@dataclass(slots=True)
class CleanupResult:
    scanned: int
    deleted: int
    reclaimed_bytes: int
    deleted_session_ids: list[str]
    skipped_pinned: int
    skipped_active: int
    decisions: list[CleanupDecision] = field(default_factory=list)


class SessionStoreProtocol(Protocol):
    def list_sessions(self) -> list[SessionRecord]:
        ...

    def touch_session(self, session_id: str, now: datetime, ttl_days: int) -> SessionRecord:
        ...

    def pin_session(self, session_id: str, pinned: bool = True) -> SessionRecord:
        ...

    def delete_session(self, session_id: str) -> None:
        ...


class FileSessionStore:
    """以 session metadata JSON 當作 SSOT。"""

    def __init__(self, sessions_dir: str | Path) -> None:
        self.sessions_dir = Path(sessions_dir)
        self.sessions_dir.mkdir(parents=True, exist_ok=True)

    def list_sessions(self) -> list[SessionRecord]:
        sessions: list[SessionRecord] = []
        for metadata_path in sorted(self.sessions_dir.glob("*.json")):
            data = self._read_json(metadata_path)
            sessions.append(self._to_record(metadata_path, data))
        return sessions

    def touch_session(self, session_id: str, now: datetime, ttl_days: int) -> SessionRecord:
        metadata_path = self._find_metadata_path(session_id)
        data = self._read_json(metadata_path)
        data["last_accessed_at"] = _format_dt(now)
        data["expires_at"] = _format_dt(now + timedelta(days=ttl_days))
        self._write_json(metadata_path, data)
        return self._to_record(metadata_path, data)

    def pin_session(self, session_id: str, pinned: bool = True) -> SessionRecord:
        metadata_path = self._find_metadata_path(session_id)
        data = self._read_json(metadata_path)
        data["pinned"] = pinned
        self._write_json(metadata_path, data)
        return self._to_record(metadata_path, data)

    def delete_session(self, session_id: str) -> None:
        metadata_path = self._find_metadata_path(session_id)
        metadata_path.unlink(missing_ok=True)

    def _find_metadata_path(self, session_id: str) -> Path:
        direct = self.sessions_dir / f"{session_id}.json"
        if direct.exists():
            return direct

        for candidate in self.sessions_dir.glob("*.json"):
            data = self._read_json(candidate)
            if str(data.get("session_id") or data.get("id")) == session_id:
                return candidate

        raise FileNotFoundError(f"找不到 session metadata: {session_id}")

    def _to_record(self, metadata_path: Path, data: dict[str, Any]) -> SessionRecord:
        session_id = str(data.get("session_id") or data.get("id") or metadata_path.stem)
        workspace_path_value = data.get("workspace_path") or data.get("sandbox_path")
        return SessionRecord(
            session_id=session_id,
            status=str(data.get("status", SessionStatus.CREATED.value)),
            pinned=bool(data.get("pinned", False)),
            created_at=_parse_dt(data.get("created_at")),
            last_accessed_at=_parse_dt(data.get("last_accessed_at")) or _parse_dt(data.get("updated_at")),
            expires_at=_parse_dt(data.get("expires_at")),
            workspace_path=Path(workspace_path_value) if workspace_path_value else None,
            metadata_path=metadata_path,
            extra=data,
        )

    @staticmethod
    def _read_json(path: Path) -> dict[str, Any]:
        return json.loads(path.read_text(encoding="utf-8"))

    @staticmethod
    def _write_json(path: Path, data: dict[str, Any]) -> None:
        path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


class SessionCleanupService:
    """依 TTL + LRU + 容量上限清理 session。"""

    ACTIVE_STATUSES = {
        SessionStatus.CREATED.value,
        SessionStatus.ACTIVE.value,
        SessionStatus.VALIDATING.value,
        SessionStatus.RUNNING.value,
    }

    def __init__(self, session_store: SessionStoreProtocol) -> None:
        self.session_store = session_store

    def touch_session(self, session_id: str, now: datetime | None = None, ttl_days: int = 3) -> SessionRecord:
        return self.session_store.touch_session(
            session_id=session_id,
            now=now or datetime.now(timezone.utc),
            ttl_days=ttl_days,
        )

    def pin_session(self, session_id: str, pinned: bool = True) -> SessionRecord:
        return self.session_store.pin_session(session_id=session_id, pinned=pinned)

    def cleanup_sessions(
        self,
        days: int = 3,
        max_sessions: int = 20,
        max_total_workspace_bytes: int | None = None,
        now: datetime | None = None,
    ) -> CleanupResult:
        now = now or datetime.now(timezone.utc)
        sessions = self.session_store.list_sessions()
        scanned = len(sessions)

        skipped_pinned = 0
        skipped_active = 0
        deleted_session_ids: list[str] = []
        reclaimed_bytes = 0
        decisions: list[CleanupDecision] = []

        ttl_threshold = now - timedelta(days=days)

        deletable: list[SessionRecord] = []
        for session in sessions:
            if session.pinned:
                skipped_pinned += 1
                continue
            if session.status in self.ACTIVE_STATUSES:
                skipped_active += 1
                continue
            deletable.append(session)

        # 先清 TTL 過期。
        remaining: list[SessionRecord] = []
        for session in sorted(deletable, key=self._sort_key):
            expired = self._is_expired(session=session, now=now, ttl_threshold=ttl_threshold)
            if not expired:
                remaining.append(session)
                continue

            reclaimed = self._delete_session(session)
            reclaimed_bytes += reclaimed
            deleted_session_ids.append(session.session_id)
            decisions.append(CleanupDecision(session_id=session.session_id, reason="ttl", reclaimed_bytes=reclaimed))

        # 再清超過 max_sessions 的部份。
        survivors = [
            session
            for session in sessions
            if session.session_id not in set(deleted_session_ids)
            and not session.pinned
            and session.status not in self.ACTIVE_STATUSES
        ]
        overflow = max(0, len(survivors) - max_sessions)
        if overflow > 0:
            for session in sorted(survivors, key=self._sort_key)[:overflow]:
                reclaimed = self._delete_session(session)
                reclaimed_bytes += reclaimed
                deleted_session_ids.append(session.session_id)
                decisions.append(CleanupDecision(session_id=session.session_id, reason="lru", reclaimed_bytes=reclaimed))

        # 最後看總磁碟大小。
        if max_total_workspace_bytes is not None:
            current = [
                session
                for session in sessions
                if session.session_id not in set(deleted_session_ids)
                and not session.pinned
                and session.status not in self.ACTIVE_STATUSES
            ]
            total_bytes = sum(self._get_workspace_size(session.workspace_path) for session in current)
            if total_bytes > max_total_workspace_bytes:
                for session in sorted(current, key=self._sort_key):
                    if total_bytes <= max_total_workspace_bytes:
                        break
                    reclaimed = self._delete_session(session)
                    total_bytes -= reclaimed
                    reclaimed_bytes += reclaimed
                    deleted_session_ids.append(session.session_id)
                    decisions.append(CleanupDecision(session_id=session.session_id, reason="disk_pressure", reclaimed_bytes=reclaimed))

        return CleanupResult(
            scanned=scanned,
            deleted=len(deleted_session_ids),
            reclaimed_bytes=reclaimed_bytes,
            deleted_session_ids=deleted_session_ids,
            skipped_pinned=skipped_pinned,
            skipped_active=skipped_active,
            decisions=decisions,
        )

    def _delete_session(self, session: SessionRecord) -> int:
        reclaimed = self._delete_workspace(session.workspace_path)
        self.session_store.delete_session(session.session_id)
        return reclaimed

    @staticmethod
    def _sort_key(session: SessionRecord) -> tuple[datetime, datetime, str]:
        epoch = datetime(1970, 1, 1, tzinfo=timezone.utc)
        last_accessed = session.last_accessed_at or session.created_at or epoch
        created_at = session.created_at or epoch
        return (last_accessed, created_at, session.session_id)

    @staticmethod
    def _is_expired(session: SessionRecord, now: datetime, ttl_threshold: datetime) -> bool:
        if session.expires_at is not None:
            return session.expires_at <= now
        reference = session.last_accessed_at or session.created_at
        if reference is None:
            return False
        return reference <= ttl_threshold

    @staticmethod
    def _get_workspace_size(workspace_path: Path | None) -> int:
        if workspace_path is None or not workspace_path.exists():
            return 0
        if workspace_path.is_file():
            return workspace_path.stat().st_size
        total = 0
        for path in workspace_path.rglob("*"):
            if path.is_file():
                total += path.stat().st_size
        return total

    def _delete_workspace(self, workspace_path: Path | None) -> int:
        reclaimed = self._get_workspace_size(workspace_path)
        if workspace_path is None or not workspace_path.exists():
            return reclaimed
        if workspace_path.is_file():
            workspace_path.unlink(missing_ok=True)
            return reclaimed
        shutil.rmtree(workspace_path, ignore_errors=True)
        return reclaimed


def _parse_dt(value: Any) -> datetime | None:
    if value in (None, ""):
        return None
    if isinstance(value, datetime):
        return value if value.tzinfo is not None else value.replace(tzinfo=timezone.utc)
    text = str(value).strip()
    if text.endswith("Z"):
        text = text[:-1] + "+00:00"
    parsed = datetime.fromisoformat(text)
    return parsed if parsed.tzinfo is not None else parsed.replace(tzinfo=timezone.utc)


def _format_dt(value: datetime) -> str:
    normalized = value if value.tzinfo is not None else value.replace(tzinfo=timezone.utc)
    return normalized.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")
