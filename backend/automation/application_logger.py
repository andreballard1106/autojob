import logging
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, List, Optional
from pathlib import Path

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.application_log import ApplicationLog
from app.models.job import JobApplication, JobStatus
from app.database import async_session_maker

logger = logging.getLogger(__name__)

SCREENSHOT_DIR = Path("storage/screenshots")
SCREENSHOT_DIR.mkdir(parents=True, exist_ok=True)


class LogAction(str, Enum):
    JOB_CREATED = "job_created"
    JOB_QUEUED = "job_queued"
    PROCESSING_STARTED = "processing_started"
    BROWSER_OPENED = "browser_opened"
    PAGE_LOADED = "page_loaded"
    PAGE_ANALYZED = "page_analyzed"
    CAPTCHA_DETECTED = "captcha_detected"
    CAPTCHA_WAITING = "captcha_waiting"
    CAPTCHA_SOLVED = "captcha_solved"
    FORM_FILLING_STARTED = "form_filling_started"
    FIELD_FILLED = "field_filled"
    FIELD_FAILED = "field_failed"
    FORM_FILLING_COMPLETED = "form_filling_completed"
    NAVIGATION_CLICKED = "navigation_clicked"
    NAVIGATION_FAILED = "navigation_failed"
    PAGE_NAVIGATED = "page_navigated"
    FILE_UPLOADED = "file_uploaded"
    SUBMIT_READY = "submit_ready"
    SUBMIT_CLICKED = "submit_clicked"
    APPLICATION_SUBMITTED = "application_submitted"
    APPLICATION_COMPLETED = "application_completed"
    APPLICATION_FAILED = "application_failed"
    RETRY_SCHEDULED = "retry_scheduled"
    STATUS_CHANGED = "status_changed"
    USER_ACTION_REQUIRED = "user_action_required"
    USER_ACTION_COMPLETED = "user_action_completed"
    ERROR = "error"
    WARNING = "warning"
    INFO = "info"


class ApplicationLogger:
    _instance = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance
    
    def __init__(self):
        if self._initialized:
            return
        self._pending_logs: List[Dict[str, Any]] = []
        self._initialized = True
    
    async def log(
        self,
        job_id: str,
        action: LogAction,
        details: Dict[str, Any] = None,
        screenshot_path: str = None,
    ) -> Optional[str]:
        try:
            async with async_session_maker() as db:
                log_entry = ApplicationLog(
                    application_id=job_id,
                    action=action.value,
                    details=details or {},
                    screenshot_path=screenshot_path,
                )
                db.add(log_entry)
                await db.commit()
                await db.refresh(log_entry)
                
                logger.debug(f"[{job_id[:8]}] Logged: {action.value}")
                return log_entry.id
                
        except Exception as e:
            logger.error(f"Failed to log action {action.value} for job {job_id}: {e}")
            self._pending_logs.append({
                "job_id": job_id,
                "action": action.value,
                "details": details,
                "screenshot_path": screenshot_path,
                "timestamp": datetime.now(timezone.utc).isoformat(),
            })
            return None
    
    def log_sync(
        self,
        job_id: str,
        action: LogAction,
        details: Dict[str, Any] = None,
        screenshot_path: str = None,
    ) -> None:
        self._pending_logs.append({
            "job_id": job_id,
            "action": action.value,
            "details": details or {},
            "screenshot_path": screenshot_path,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        })
    
    async def flush_pending_logs(self) -> int:
        if not self._pending_logs:
            return 0
        
        flushed = 0
        try:
            async with async_session_maker() as db:
                for log_data in self._pending_logs:
                    log_entry = ApplicationLog(
                        application_id=log_data["job_id"],
                        action=log_data["action"],
                        details=log_data.get("details", {}),
                        screenshot_path=log_data.get("screenshot_path"),
                    )
                    db.add(log_entry)
                    flushed += 1
                
                await db.commit()
                self._pending_logs.clear()
                
        except Exception as e:
            logger.error(f"Failed to flush pending logs: {e}")
        
        return flushed
    
    async def log_status_change(
        self,
        job_id: str,
        old_status: str,
        new_status: str,
        reason: str = None,
    ) -> None:
        await self.log(
            job_id=job_id,
            action=LogAction.STATUS_CHANGED,
            details={
                "old_status": old_status,
                "new_status": new_status,
                "reason": reason,
            },
        )
    
    async def log_processing_started(
        self,
        job_id: str,
        url: str,
        profile_id: str,
    ) -> None:
        await self.log(
            job_id=job_id,
            action=LogAction.PROCESSING_STARTED,
            details={
                "url": url,
                "profile_id": profile_id,
            },
        )
    
    async def log_page_loaded(
        self,
        job_id: str,
        url: str,
        title: str,
        page_number: int = 1,
    ) -> None:
        await self.log(
            job_id=job_id,
            action=LogAction.PAGE_LOADED,
            details={
                "url": url,
                "title": title,
                "page_number": page_number,
            },
        )
    
    async def log_captcha_detected(
        self,
        job_id: str,
        captcha_type: str,
        confidence: float,
    ) -> None:
        await self.log(
            job_id=job_id,
            action=LogAction.CAPTCHA_DETECTED,
            details={
                "captcha_type": captcha_type,
                "confidence": confidence,
            },
        )
    
    async def log_form_filling(
        self,
        job_id: str,
        fields_filled: int,
        fields_failed: int,
        unmapped_fields: List[str] = None,
    ) -> None:
        await self.log(
            job_id=job_id,
            action=LogAction.FORM_FILLING_COMPLETED,
            details={
                "fields_filled": fields_filled,
                "fields_failed": fields_failed,
                "unmapped_fields": unmapped_fields or [],
            },
        )
    
    async def log_field_action(
        self,
        job_id: str,
        field_name: str,
        selector: str,
        action_type: str,
        success: bool,
        error: str = None,
    ) -> None:
        await self.log(
            job_id=job_id,
            action=LogAction.FIELD_FILLED if success else LogAction.FIELD_FAILED,
            details={
                "field_name": field_name,
                "selector": selector,
                "action_type": action_type,
                "success": success,
                "error": error,
            },
        )
    
    async def log_error(
        self,
        job_id: str,
        error_message: str,
        error_type: str = None,
        stack_trace: str = None,
    ) -> None:
        await self.log(
            job_id=job_id,
            action=LogAction.ERROR,
            details={
                "error_message": error_message,
                "error_type": error_type,
                "stack_trace": stack_trace,
            },
        )
    
    async def log_application_result(
        self,
        job_id: str,
        success: bool,
        fields_filled: int,
        fields_failed: int,
        submit_ready: bool,
        error_message: str = None,
    ) -> None:
        action = LogAction.APPLICATION_COMPLETED if success else LogAction.APPLICATION_FAILED
        await self.log(
            job_id=job_id,
            action=action,
            details={
                "success": success,
                "fields_filled": fields_filled,
                "fields_failed": fields_failed,
                "submit_ready": submit_ready,
                "error_message": error_message,
            },
        )
    
    async def get_job_history(
        self,
        job_id: str,
        limit: int = 100,
    ) -> List[Dict[str, Any]]:
        try:
            async with async_session_maker() as db:
                query = (
                    select(ApplicationLog)
                    .where(ApplicationLog.application_id == job_id)
                    .order_by(ApplicationLog.created_at.desc())
                    .limit(limit)
                )
                result = await db.execute(query)
                logs = result.scalars().all()
                
                return [
                    {
                        "id": log.id,
                        "action": log.action,
                        "details": log.details,
                        "screenshot_path": log.screenshot_path,
                        "created_at": log.created_at.isoformat(),
                    }
                    for log in logs
                ]
        except Exception as e:
            logger.error(f"Failed to get history for job {job_id}: {e}")
            return []
    
    async def get_job_summary(self, job_id: str) -> Dict[str, Any]:
        history = await self.get_job_history(job_id, limit=500)
        
        summary = {
            "total_actions": len(history),
            "fields_filled": 0,
            "fields_failed": 0,
            "pages_processed": 0,
            "captcha_encounters": 0,
            "errors": 0,
            "last_action": None,
            "first_action": None,
        }
        
        for log in history:
            action = log["action"]
            details = log.get("details", {})
            
            if action == LogAction.FIELD_FILLED.value:
                summary["fields_filled"] += 1
            elif action == LogAction.FIELD_FAILED.value:
                summary["fields_failed"] += 1
            elif action == LogAction.PAGE_LOADED.value:
                summary["pages_processed"] += 1
            elif action == LogAction.CAPTCHA_DETECTED.value:
                summary["captcha_encounters"] += 1
            elif action == LogAction.ERROR.value:
                summary["errors"] += 1
            elif action == LogAction.FORM_FILLING_COMPLETED.value:
                summary["fields_filled"] = details.get("fields_filled", summary["fields_filled"])
                summary["fields_failed"] = details.get("fields_failed", summary["fields_failed"])
        
        if history:
            summary["last_action"] = history[0]
            summary["first_action"] = history[-1]
        
        return summary


application_logger = ApplicationLogger()

