import pytest
import tempfile
import shutil
from pathlib import Path
from unittest.mock import Mock

from automation.notification_service import (
    NotificationService,
    NotificationType,
    NotificationPriority,
    SystemNotification,
)


@pytest.fixture
def temp_storage_dir():
    temp_dir = Path(tempfile.mkdtemp())
    yield temp_dir
    shutil.rmtree(temp_dir, ignore_errors=True)


@pytest.fixture
def notification_svc(temp_storage_dir):
    svc = NotificationService.__new__(NotificationService)
    svc._initialized = False
    svc._notifications = []
    svc._subscribers = []
    svc._pending_queue = []
    svc._storage_path = temp_storage_dir
    svc._storage_path.mkdir(parents=True, exist_ok=True)
    svc._initialized = True
    return svc


class TestSystemNotification:
    def test_create_notification(self):
        notification = SystemNotification(
            notification_type=NotificationType.CAPTCHA_DETECTED,
            title="CAPTCHA Detected",
            message="Please solve the CAPTCHA",
            job_id="job-123",
        )
        
        assert notification.notification_type == NotificationType.CAPTCHA_DETECTED
        assert notification.title == "CAPTCHA Detected"
        assert notification.job_id == "job-123"
        assert notification.created_at != ""
    
    def test_default_priority(self):
        notification = SystemNotification(
            notification_type=NotificationType.INFO,
            title="Info",
            message="Some info",
        )
        
        assert notification.priority == NotificationPriority.NORMAL
    
    def test_to_dict(self):
        notification = SystemNotification(
            notification_type=NotificationType.JOB_COMPLETED,
            title="Job Completed",
            message="Job has finished",
            job_id="job-456",
            priority=NotificationPriority.HIGH,
        )
        
        data = notification.to_dict()
        
        assert data["type"] == "job_completed"
        assert data["title"] == "Job Completed"
        assert data["job_id"] == "job-456"
        assert data["priority"] == "high"


class TestNotificationService:
    def test_notify_creates_notification(self, notification_svc):
        notification = SystemNotification(
            notification_type=NotificationType.INFO,
            title="Test",
            message="Test message",
        )
        
        notification_svc.notify(notification)
        
        assert len(notification_svc._notifications) == 1
    
    def test_subscribe_and_notify(self, notification_svc):
        callback_received = []
        
        def callback(n):
            callback_received.append(n)
        
        notification_svc.subscribe(callback)
        
        notification = SystemNotification(
            notification_type=NotificationType.INFO,
            title="Test",
            message="Test",
        )
        notification_svc.notify(notification)
        
        assert len(callback_received) == 1
        assert callback_received[0].title == "Test"
    
    def test_unsubscribe(self, notification_svc):
        callback_received = []
        
        def callback(n):
            callback_received.append(n)
        
        notification_svc.subscribe(callback)
        notification_svc.unsubscribe(callback)
        
        notification = SystemNotification(
            notification_type=NotificationType.INFO,
            title="Test",
            message="Test",
        )
        notification_svc.notify(notification)
        
        assert len(callback_received) == 0


class TestNotificationServiceHelpers:
    def test_notify_captcha_detected(self, notification_svc):
        notification = notification_svc.notify_captcha_detected(
            job_id="job-123",
            profile_id="profile-456",
            captcha_type="recaptcha",
            url="https://example.com",
        )
        
        assert notification.notification_type == NotificationType.CAPTCHA_DETECTED
        assert notification.priority == NotificationPriority.URGENT
        assert notification.requires_action == True
        assert notification.data["captcha_type"] == "recaptcha"
    
    def test_notify_job_paused(self, notification_svc):
        notification = notification_svc.notify_job_paused(
            job_id="job-123",
            reason="Manual intervention required",
        )
        
        assert notification.notification_type == NotificationType.JOB_PAUSED
        assert notification.priority == NotificationPriority.HIGH
        assert notification.requires_action == True
    
    def test_notify_job_completed_ready(self, notification_svc):
        notification = notification_svc.notify_job_completed(
            job_id="job-123",
            fields_filled=15,
            submit_ready=True,
        )
        
        assert notification.notification_type == NotificationType.JOB_COMPLETED
        assert "Ready for Submission" in notification.title
        assert notification.data["submit_ready"] == True
    
    def test_notify_job_completed_not_ready(self, notification_svc):
        notification = notification_svc.notify_job_completed(
            job_id="job-123",
            fields_filled=10,
            submit_ready=False,
        )
        
        assert "Completed" in notification.title
        assert notification.data["submit_ready"] == False
    
    def test_notify_job_failed(self, notification_svc):
        notification = notification_svc.notify_job_failed(
            job_id="job-123",
            error="Connection timeout",
        )
        
        assert notification.notification_type == NotificationType.JOB_FAILED
        assert notification.priority == NotificationPriority.HIGH
        assert "Connection timeout" in notification.message


class TestNotificationFiltering:
    def test_get_notifications_limit(self, notification_svc):
        for i in range(10):
            notification_svc.notify(SystemNotification(
                notification_type=NotificationType.INFO,
                title=f"Notification {i}",
                message="Test",
            ))
        
        result = notification_svc.get_notifications(limit=5)
        
        assert len(result) == 5
    
    def test_get_notifications_by_job_id(self, notification_svc):
        notification_svc.notify(SystemNotification(
            notification_type=NotificationType.INFO,
            title="Job A",
            message="Test",
            job_id="job-a",
        ))
        notification_svc.notify(SystemNotification(
            notification_type=NotificationType.INFO,
            title="Job B",
            message="Test",
            job_id="job-b",
        ))
        
        result = notification_svc.get_notifications(job_id="job-a")
        
        assert len(result) == 1
        assert result[0].job_id == "job-a"
    
    def test_get_pending_actions(self, notification_svc):
        notification_svc.notify(SystemNotification(
            notification_type=NotificationType.INFO,
            title="Info",
            message="Test",
            requires_action=False,
        ))
        notification_svc.notify(SystemNotification(
            notification_type=NotificationType.CAPTCHA_DETECTED,
            title="CAPTCHA",
            message="Test",
            requires_action=True,
        ))
        
        pending = notification_svc.get_pending_actions()
        
        assert len(pending) == 1
        assert pending[0].requires_action == True
    
    def test_clear_notifications_by_job(self, notification_svc):
        notification_svc.notify(SystemNotification(
            notification_type=NotificationType.INFO,
            title="Job A",
            message="Test",
            job_id="job-a",
        ))
        notification_svc.notify(SystemNotification(
            notification_type=NotificationType.INFO,
            title="Job B",
            message="Test",
            job_id="job-b",
        ))
        
        cleared = notification_svc.clear_notifications(job_id="job-a")
        
        assert cleared == 1
        assert len(notification_svc._notifications) == 1
    
    def test_clear_all_notifications(self, notification_svc):
        for i in range(5):
            notification_svc.notify(SystemNotification(
                notification_type=NotificationType.INFO,
                title=f"Notification {i}",
                message="Test",
            ))
        
        cleared = notification_svc.clear_notifications()
        
        assert cleared == 5
        assert len(notification_svc._notifications) == 0

