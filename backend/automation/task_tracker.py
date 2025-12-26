"""
Background Task Tracker for Job Processing

Properly manages async tasks to prevent:
- Tasks being garbage collected
- Silent exception drops
- Duplicate processing
"""

import asyncio
import logging
import threading
from datetime import datetime, timezone
from typing import Dict, Set, Optional, Any
from dataclasses import dataclass, field

logger = logging.getLogger(__name__)


@dataclass
class TaskInfo:
    """Information about a background processing task."""
    task_id: str
    job_ids: list
    created_at: str = ""
    status: str = "running"
    error: Optional[str] = None
    
    def __post_init__(self):
        if not self.created_at:
            self.created_at = datetime.now(timezone.utc).isoformat()


class TaskTracker:
    """
    Thread-safe tracker for background processing tasks.
    
    Ensures:
    - Tasks are not garbage collected
    - Exceptions are properly logged
    - Duplicate processing is prevented
    """
    
    _instance = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance
    
    def __init__(self):
        if self._initialized:
            return
        
        self._active_tasks: Dict[str, asyncio.Task] = {}
        self._task_info: Dict[str, TaskInfo] = {}
        self._processing_job_ids: Set[str] = set()
        self._lock = threading.Lock()
        self._initialized = True
    
    def is_job_processing(self, job_id: str) -> bool:
        """Check if a job is currently being processed."""
        with self._lock:
            return job_id in self._processing_job_ids
    
    def get_processing_job_ids(self) -> Set[str]:
        """Get all job IDs currently being processed."""
        with self._lock:
            return self._processing_job_ids.copy()
    
    def filter_non_processing_jobs(self, job_ids: list) -> list:
        """Filter out jobs that are already being processed."""
        with self._lock:
            return [jid for jid in job_ids if jid not in self._processing_job_ids]
    
    def _mark_jobs_processing(self, job_ids: list) -> None:
        """Mark jobs as currently processing."""
        with self._lock:
            for jid in job_ids:
                self._processing_job_ids.add(jid)
    
    def _unmark_jobs_processing(self, job_ids: list) -> None:
        """Remove jobs from processing set."""
        with self._lock:
            for jid in job_ids:
                self._processing_job_ids.discard(jid)
    
    def create_task(
        self,
        task_id: str,
        coro,
        job_ids: list,
    ) -> Optional[asyncio.Task]:
        """
        Create and track a background task.
        
        Args:
            task_id: Unique identifier for the task
            coro: The coroutine to run
            job_ids: List of job IDs being processed
            
        Returns:
            The created task, or None if all jobs are already processing
        """
        # Filter out jobs that are already being processed
        new_job_ids = self.filter_non_processing_jobs(job_ids)
        
        if not new_job_ids:
            logger.warning(f"Task {task_id}: All jobs are already being processed")
            return None
        
        # Mark jobs as processing
        self._mark_jobs_processing(new_job_ids)
        
        # Create wrapper that handles cleanup
        async def task_wrapper():
            try:
                # Update the coro's job_ids to only include non-processing ones
                await coro
            except Exception as e:
                logger.error(f"Task {task_id} failed with error: {e}")
                import traceback
                traceback.print_exc()
                with self._lock:
                    if task_id in self._task_info:
                        self._task_info[task_id].status = "failed"
                        self._task_info[task_id].error = str(e)
            finally:
                # Clean up
                self._unmark_jobs_processing(new_job_ids)
                with self._lock:
                    if task_id in self._active_tasks:
                        del self._active_tasks[task_id]
                    if task_id in self._task_info:
                        if self._task_info[task_id].status == "running":
                            self._task_info[task_id].status = "completed"
        
        # Create the task
        task = asyncio.create_task(task_wrapper())
        
        # Store references
        with self._lock:
            self._active_tasks[task_id] = task
            self._task_info[task_id] = TaskInfo(
                task_id=task_id,
                job_ids=new_job_ids,
            )
        
        logger.info(f"Created task {task_id} for {len(new_job_ids)} jobs")
        return task
    
    def get_active_task_count(self) -> int:
        """Get number of active tasks."""
        with self._lock:
            return len(self._active_tasks)
    
    def get_task_info(self, task_id: str) -> Optional[TaskInfo]:
        """Get information about a task."""
        with self._lock:
            return self._task_info.get(task_id)
    
    def get_all_task_info(self) -> Dict[str, TaskInfo]:
        """Get information about all tasks."""
        with self._lock:
            return dict(self._task_info)
    
    def cancel_task(self, task_id: str) -> bool:
        """Cancel a running task."""
        with self._lock:
            task = self._active_tasks.get(task_id)
            if task and not task.done():
                task.cancel()
                return True
        return False
    
    async def cancel_all_tasks(self) -> int:
        """Cancel all running tasks."""
        cancelled = 0
        with self._lock:
            task_ids = list(self._active_tasks.keys())
        
        for task_id in task_ids:
            if self.cancel_task(task_id):
                cancelled += 1
        
        return cancelled
    
    def cleanup_completed(self) -> int:
        """Remove completed task info older than 1 hour."""
        from datetime import timedelta
        
        cutoff = datetime.now(timezone.utc) - timedelta(hours=1)
        removed = 0
        
        with self._lock:
            to_remove = []
            for task_id, info in self._task_info.items():
                if task_id not in self._active_tasks:
                    try:
                        created = datetime.fromisoformat(info.created_at.replace('Z', '+00:00'))
                        if created < cutoff:
                            to_remove.append(task_id)
                    except Exception:
                        pass
            
            for task_id in to_remove:
                del self._task_info[task_id]
                removed += 1
        
        return removed


# Global singleton instance
task_tracker = TaskTracker()

