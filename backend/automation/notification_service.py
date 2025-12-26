import json
import logging
import asyncio
import threading
from dataclasses import dataclass, asdict
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Callable, Dict, List, Optional
from pathlib import Path

logger = logging.getLogger(__name__)


class NotificationType(str, Enum):
    CAPTCHA_DETECTED = "captcha_detected"
    JOB_STARTED = "job_started"
    JOB_COMPLETED = "job_completed"
    JOB_FAILED = "job_failed"
    JOB_PAUSED = "job_paused"
    ACTION_REQUIRED = "action_required"
    FORM_FILLED = "form_filled"
    SUBMIT_READY = "submit_ready"
    ERROR = "error"
    INFO = "info"


class NotificationPriority(str, Enum):
    LOW = "low"
    NORMAL = "normal"
    HIGH = "high"
    URGENT = "urgent"


@dataclass
class SystemNotification:
    notification_type: NotificationType
    title: str
    message: str
    job_id: Optional[str] = None
    profile_id: Optional[str] = None
    priority: NotificationPriority = NotificationPriority.NORMAL
    data: Dict[str, Any] = None
    action_url: Optional[str] = None
    requires_action: bool = False
    created_at: str = ""
    
    def __post_init__(self):
        if not self.created_at:
            self.created_at = datetime.now(timezone.utc).isoformat()
        self.data = self.data or {}
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "type": self.notification_type.value,
            "title": self.title,
            "message": self.message,
            "job_id": self.job_id,
            "profile_id": self.profile_id,
            "priority": self.priority.value,
            "data": self.data,
            "action_url": self.action_url,
            "requires_action": self.requires_action,
            "created_at": self.created_at,
        }


NOTIFICATION_STORAGE_PATH = Path("storage/notifications")


class NotificationService:
    _instance = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance
    
    def __init__(self):
        if self._initialized:
            return
        
        self._notifications: List[SystemNotification] = []
        self._subscribers: List[Callable] = []
        self._pending_queue: List[SystemNotification] = []
        self._storage_path = NOTIFICATION_STORAGE_PATH
        self._storage_path.mkdir(parents=True, exist_ok=True)
        self._lock = threading.Lock()  # Thread-safe access to notifications
        self._initialized = True
    
    def subscribe(self, callback: Callable[[SystemNotification], None]) -> None:
        with self._lock:
            self._subscribers.append(callback)
    
    def unsubscribe(self, callback: Callable) -> None:
        with self._lock:
            if callback in self._subscribers:
                self._subscribers.remove(callback)
    
    def notify(self, notification: SystemNotification) -> None:
        with self._lock:
            self._notifications.append(notification)
            subscribers_copy = self._subscribers.copy()
        
        self._save_notification(notification)
        
        for subscriber in subscribers_copy:
            try:
                subscriber(notification)
            except Exception as e:
                logger.error(f"Error notifying subscriber: {e}")
        
        self._log_notification(notification)
    
    def notify_captcha_detected(
        self,
        job_id: str,
        profile_id: str = None,
        captcha_type: str = "unknown",
        url: str = None,
    ) -> SystemNotification:
        notification = SystemNotification(
            notification_type=NotificationType.CAPTCHA_DETECTED,
            title="CAPTCHA Detected - Action Required",
            message=f"A {captcha_type} CAPTCHA was detected on the job application page. Please solve it manually to continue.",
            job_id=job_id,
            profile_id=profile_id,
            priority=NotificationPriority.URGENT,
            requires_action=True,
            data={
                "captcha_type": captcha_type,
                "url": url,
            },
            action_url=f"/jobs/{job_id}",
        )
        
        self.notify(notification)
        return notification
    
    def notify_job_paused(
        self,
        job_id: str,
        reason: str,
        profile_id: str = None,
    ) -> SystemNotification:
        notification = SystemNotification(
            notification_type=NotificationType.JOB_PAUSED,
            title="Job Processing Paused",
            message=reason,
            job_id=job_id,
            profile_id=profile_id,
            priority=NotificationPriority.HIGH,
            requires_action=True,
            action_url=f"/jobs/{job_id}",
        )
        
        self.notify(notification)
        return notification
    
    def notify_action_required(
        self,
        job_id: str,
        action_type: str,
        message: str,
        profile_id: str = None,
    ) -> SystemNotification:
        notification = SystemNotification(
            notification_type=NotificationType.ACTION_REQUIRED,
            title=f"Action Required: {action_type}",
            message=message,
            job_id=job_id,
            profile_id=profile_id,
            priority=NotificationPriority.HIGH,
            requires_action=True,
            data={"action_type": action_type},
            action_url=f"/jobs/{job_id}",
        )
        
        self.notify(notification)
        return notification
    
    def notify_job_completed(
        self,
        job_id: str,
        fields_filled: int,
        submit_ready: bool,
        profile_id: str = None,
    ) -> SystemNotification:
        if submit_ready:
            title = "Application Ready for Submission"
            message = f"Job application has been filled with {fields_filled} fields and is ready for submission."
        else:
            title = "Application Processing Completed"
            message = f"Job application processing completed. {fields_filled} fields were filled."
        
        notification = SystemNotification(
            notification_type=NotificationType.JOB_COMPLETED,
            title=title,
            message=message,
            job_id=job_id,
            profile_id=profile_id,
            priority=NotificationPriority.NORMAL,
            data={
                "fields_filled": fields_filled,
                "submit_ready": submit_ready,
            },
            action_url=f"/jobs/{job_id}",
        )
        
        self.notify(notification)
        return notification
    
    def notify_job_failed(
        self,
        job_id: str,
        error: str,
        profile_id: str = None,
    ) -> SystemNotification:
        notification = SystemNotification(
            notification_type=NotificationType.JOB_FAILED,
            title="Job Processing Failed",
            message=f"An error occurred while processing the job application: {error[:200]}",
            job_id=job_id,
            profile_id=profile_id,
            priority=NotificationPriority.HIGH,
            data={"error": error},
            action_url=f"/jobs/{job_id}",
        )
        
        self.notify(notification)
        return notification
    
    def notify_error(
        self,
        message: str,
        job_id: str = None,
        profile_id: str = None,
        error_details: str = None,
    ) -> SystemNotification:
        notification = SystemNotification(
            notification_type=NotificationType.ERROR,
            title="Error",
            message=message,
            job_id=job_id,
            profile_id=profile_id,
            priority=NotificationPriority.HIGH,
            data={"details": error_details} if error_details else {},
        )
        
        self.notify(notification)
        return notification
    
    def get_notifications(
        self,
        limit: int = 50,
        job_id: str = None,
        notification_type: NotificationType = None,
        unread_only: bool = False,
    ) -> List[SystemNotification]:
        with self._lock:
            filtered = self._notifications.copy()
        
        if job_id:
            filtered = [n for n in filtered if n.job_id == job_id]
        
        if notification_type:
            filtered = [n for n in filtered if n.notification_type == notification_type]
        
        filtered.sort(key=lambda x: x.created_at, reverse=True)
        
        return filtered[:limit]
    
    def get_pending_actions(self) -> List[SystemNotification]:
        with self._lock:
            return [n for n in self._notifications if n.requires_action]
    
    def clear_notifications(self, job_id: str = None) -> int:
        with self._lock:
            if job_id:
                original_count = len(self._notifications)
                self._notifications = [n for n in self._notifications if n.job_id != job_id]
                return original_count - len(self._notifications)
            else:
                count = len(self._notifications)
                self._notifications.clear()
                return count
    
    def _save_notification(self, notification: SystemNotification) -> None:
        try:
            file_path = self._storage_path / f"{notification.job_id or 'system'}.jsonl"
            with open(file_path, "a", encoding="utf-8") as f:
                f.write(json.dumps(notification.to_dict()) + "\n")
        except Exception as e:
            logger.error(f"Failed to save notification: {e}")
    
    def _log_notification(self, notification: SystemNotification) -> None:
        prefix = {
            NotificationPriority.URGENT: "[URGENT]",
            NotificationPriority.HIGH: "[HIGH]",
            NotificationPriority.NORMAL: "[INFO]",
            NotificationPriority.LOW: "[LOW]",
        }.get(notification.priority, "[INFO]")
        
        print(f"\n{'='*60}")
        print(f"{prefix} NOTIFICATION: {notification.title}")
        print(f"  {notification.message}")
        if notification.job_id:
            print(f"  Job ID: {notification.job_id}")
        if notification.requires_action:
            print(f"  ** ACTION REQUIRED **")
        print(f"{'='*60}\n")


notification_service = NotificationService()

