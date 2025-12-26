import json
import os
import time
import shutil
import logging
import threading
from dataclasses import dataclass, asdict, field
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
from pathlib import Path

logger = logging.getLogger(__name__)


STORAGE_DIR = Path("storage/sessions")


@dataclass
class PageSnapshot:
    url: str
    title: str
    filtered_html: str
    inputs: List[Dict[str, Any]]
    buttons: List[Dict[str, Any]]
    forms: List[Dict[str, Any]]
    timestamp: str = ""
    page_number: int = 1
    
    def __post_init__(self):
        if not self.timestamp:
            self.timestamp = datetime.now(timezone.utc).isoformat()
    
    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "PageSnapshot":
        return cls(
            url=data.get("url", ""),
            title=data.get("title", ""),
            filtered_html=data.get("filtered_html", ""),
            inputs=data.get("inputs", []),
            buttons=data.get("buttons", []),
            forms=data.get("forms", []),
            timestamp=data.get("timestamp", ""),
            page_number=data.get("page_number", 1),
        )


@dataclass
class AutofillResult:
    field_name: str
    selector: str
    action: str
    value: Any
    success: bool
    error: Optional[str] = None
    duration_ms: int = 0


@dataclass
class ApplicationSession:
    job_id: str
    profile_id: str
    url: str
    status: str = "active"
    current_page: int = 1
    page_snapshots: List[PageSnapshot] = field(default_factory=list)
    autofill_results: List[AutofillResult] = field(default_factory=list)
    navigation_history: List[str] = field(default_factory=list)
    created_at: str = ""
    updated_at: str = ""
    error_message: Optional[str] = None
    # Platform-specific metadata storage (e.g., job description for Workday)
    metadata: Dict[str, Any] = field(default_factory=dict)
    # Detected platform (workday, greenhouse, etc.)
    platform: str = "unknown"
    
    def __post_init__(self):
        now = datetime.now(timezone.utc).isoformat()
        if not self.created_at:
            self.created_at = now
        if not self.updated_at:
            self.updated_at = now
        if self.metadata is None:
            self.metadata = {}
    
    def add_page_snapshot(self, snapshot: PageSnapshot) -> None:
        snapshot.page_number = len(self.page_snapshots) + 1
        self.page_snapshots.append(snapshot)
        self.current_page = snapshot.page_number
        self.updated_at = datetime.now(timezone.utc).isoformat()
    
    def add_autofill_result(self, result: AutofillResult) -> None:
        self.autofill_results.append(result)
        self.updated_at = datetime.now(timezone.utc).isoformat()
    
    def add_navigation(self, url: str) -> None:
        self.navigation_history.append(url)
        self.updated_at = datetime.now(timezone.utc).isoformat()
    
    def get_latest_snapshot(self) -> Optional[PageSnapshot]:
        return self.page_snapshots[-1] if self.page_snapshots else None
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "job_id": self.job_id,
            "profile_id": self.profile_id,
            "url": self.url,
            "status": self.status,
            "current_page": self.current_page,
            "page_snapshots": [s.to_dict() for s in self.page_snapshots],
            "autofill_results": [asdict(r) for r in self.autofill_results],
            "navigation_history": self.navigation_history,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
            "error_message": self.error_message,
            "metadata": self.metadata,
            "platform": self.platform,
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "ApplicationSession":
        session = cls(
            job_id=data.get("job_id", ""),
            profile_id=data.get("profile_id", ""),
            url=data.get("url", ""),
            status=data.get("status", "active"),
            current_page=data.get("current_page", 1),
            navigation_history=data.get("navigation_history", []),
            created_at=data.get("created_at", ""),
            updated_at=data.get("updated_at", ""),
            error_message=data.get("error_message"),
            metadata=data.get("metadata", {}),
            platform=data.get("platform", "unknown"),
        )
        
        for snap_data in data.get("page_snapshots", []):
            session.page_snapshots.append(PageSnapshot.from_dict(snap_data))
        
        for result_data in data.get("autofill_results", []):
            session.autofill_results.append(AutofillResult(**result_data))
        
        return session


class SessionStorage:
    def __init__(self, storage_dir: Path = None):
        self.storage_dir = storage_dir or STORAGE_DIR
        self.storage_dir.mkdir(parents=True, exist_ok=True)
        self._sessions: Dict[str, ApplicationSession] = {}
        self._lock = threading.Lock()  # Thread-safe access to sessions
    
    def _get_session_path(self, job_id: str) -> Path:
        return self.storage_dir / f"{job_id}.json"
    
    def create_session(
        self,
        job_id: str,
        profile_id: str,
        url: str,
    ) -> ApplicationSession:
        session = ApplicationSession(
            job_id=job_id,
            profile_id=profile_id,
            url=url,
        )
        session.add_navigation(url)
        
        with self._lock:
            self._sessions[job_id] = session
        self._save_session(session)
        
        return session
    
    def get_session(self, job_id: str) -> Optional[ApplicationSession]:
        with self._lock:
            if job_id in self._sessions:
                return self._sessions[job_id]
        
        session_path = self._get_session_path(job_id)
        if session_path.exists():
            try:
                with open(session_path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                session = ApplicationSession.from_dict(data)
                with self._lock:
                    self._sessions[job_id] = session
                return session
            except Exception as e:
                logger.error(f"Failed to load session {job_id}: {e}")
        
        return None
    
    def update_session(self, session: ApplicationSession) -> None:
        session.updated_at = datetime.now(timezone.utc).isoformat()
        with self._lock:
            self._sessions[session.job_id] = session
        self._save_session(session)
    
    def add_page_snapshot(
        self,
        job_id: str,
        page_content: Dict[str, Any],
    ) -> Optional[PageSnapshot]:
        session = self.get_session(job_id)
        if not session:
            return None
        
        snapshot = PageSnapshot(
            url=page_content.get("url", ""),
            title=page_content.get("title", ""),
            filtered_html=page_content.get("filtered_html", ""),
            inputs=page_content.get("inputs", []),
            buttons=page_content.get("buttons", []),
            forms=page_content.get("forms", []),
        )
        
        session.add_page_snapshot(snapshot)
        self._save_session(session)
        
        return snapshot
    
    def add_autofill_results(
        self,
        job_id: str,
        results: List[Dict[str, Any]],
    ) -> None:
        session = self.get_session(job_id)
        if not session:
            return
        
        for result in results:
            session.add_autofill_result(AutofillResult(
                field_name=result.get("field_name", ""),
                selector=result.get("selector", ""),
                action=result.get("action", ""),
                value=result.get("value"),
                success=result.get("success", False),
                error=result.get("error"),
                duration_ms=result.get("duration_ms", 0),
            ))
        
        self._save_session(session)
    
    def set_session_status(
        self,
        job_id: str,
        status: str,
        error_message: Optional[str] = None,
    ) -> None:
        session = self.get_session(job_id)
        if session:
            session.status = status
            session.error_message = error_message
            self._save_session(session)
    
    def set_session_metadata(
        self,
        job_id: str,
        key: str,
        value: Any,
    ) -> None:
        """Store platform-specific metadata in session."""
        session = self.get_session(job_id)
        if session:
            session.metadata[key] = value
            self._save_session(session)
    
    def get_session_metadata(
        self,
        job_id: str,
        key: str,
        default: Any = None,
    ) -> Any:
        """Retrieve platform-specific metadata from session."""
        session = self.get_session(job_id)
        if session and session.metadata:
            return session.metadata.get(key, default)
        return default
    
    def set_session_platform(
        self,
        job_id: str,
        platform: str,
    ) -> None:
        """Set the detected platform for a session."""
        session = self.get_session(job_id)
        if session:
            session.platform = platform
            self._save_session(session)
    
    def delete_session(self, job_id: str) -> bool:
        with self._lock:
            if job_id in self._sessions:
                del self._sessions[job_id]
        
        session_path = self._get_session_path(job_id)
        if session_path.exists():
            try:
                session_path.unlink()
                return True
            except Exception as e:
                logger.error(f"Failed to delete session file {job_id}: {e}")
        
        return False
    
    def get_all_active_sessions(self) -> List[ApplicationSession]:
        active = []
        
        with self._lock:
            for session in self._sessions.values():
                if session.status == "active":
                    active.append(session)
            cached_job_ids = set(self._sessions.keys())
        
        for session_file in self.storage_dir.glob("*.json"):
            job_id = session_file.stem
            if job_id not in cached_job_ids:
                session = self.get_session(job_id)
                if session and session.status == "active":
                    active.append(session)
        
        return active
    
    def cleanup_old_sessions(self, max_age_hours: int = 24) -> int:
        deleted_count = 0
        cutoff = time.time() - (max_age_hours * 3600)
        
        for session_file in self.storage_dir.glob("*.json"):
            if session_file.stat().st_mtime < cutoff:
                try:
                    session_file.unlink()
                    job_id = session_file.stem
                    with self._lock:
                        if job_id in self._sessions:
                            del self._sessions[job_id]
                    deleted_count += 1
                except Exception as e:
                    logger.error(f"Failed to cleanup session: {e}")
        
        return deleted_count
    
    def _save_session(self, session: ApplicationSession) -> None:
        session_path = self._get_session_path(session.job_id)
        try:
            # Use atomic write: write to temp file then rename
            temp_path = session_path.with_suffix('.json.tmp')
            with open(temp_path, "w", encoding="utf-8") as f:
                json.dump(session.to_dict(), f, indent=2, ensure_ascii=False)
            # Atomic rename (on most filesystems)
            temp_path.replace(session_path)
        except Exception as e:
            logger.error(f"Failed to save session {session.job_id}: {e}")


session_storage = SessionStorage()

