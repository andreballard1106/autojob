"""
Base workflow handler for job application automation.

This module defines the abstract base class that all platform-specific
workflow handlers must implement.
"""

import logging
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


@dataclass
class WorkflowResult:
    """Result from a workflow handler processing a page or application."""
    success: bool
    page_number: int = 1
    fields_filled: int = 0
    fields_failed: int = 0
    needs_more_navigation: bool = False
    submit_ready: bool = False
    error: Optional[str] = None
    unmapped_fields: List[str] = field(default_factory=list)
    captcha_detected: bool = False
    captcha_type: Optional[str] = None
    paused: bool = False
    pause_reason: Optional[str] = None
    platform: str = "unknown"
    
    def __post_init__(self):
        if self.unmapped_fields is None:
            self.unmapped_fields = []


class BaseWorkflowHandler(ABC):
    """
    Abstract base class for platform-specific workflow handlers.
    
    Each platform (Workday, Greenhouse, Lever, etc.) can have its own
    implementation with optimizations for that platform's specific
    form structure, navigation patterns, and quirks.
    
    Subclasses must implement:
    - process_page(): Handle a single page
    - process_application(): Handle the entire application flow
    - get_platform_name(): Return the platform identifier
    """
    
    # Class-level platform identifier
    PLATFORM_NAME: str = "base"
    
    # Known URL patterns for this platform (used for auto-detection)
    URL_PATTERNS: List[str] = []
    
    def __init__(
        self,
        driver,
        ai_service,
        profile_data: Dict[str, Any],
        job_id: str,
        storage=None,
        detector=None,
        notifier=None,
        app_logger=None,
    ):
        """
        Initialize the workflow handler.
        
        Args:
            driver: Selenium WebDriver instance
            ai_service: AIService for page analysis
            profile_data: User profile data for form filling
            job_id: Job application ID
            storage: Session storage service
            detector: CAPTCHA detector
            notifier: Notification service
            app_logger: Application logger
        """
        self.driver = driver
        self.ai_service = ai_service
        self.profile_data = profile_data
        self.job_id = job_id
        self.storage = storage
        self.captcha_detector = detector
        self.notifier = notifier
        self.app_logger = app_logger
        
        self._last_ai_response = None
    
    @classmethod
    def get_platform_name(cls) -> str:
        """Return the platform identifier for this handler."""
        return cls.PLATFORM_NAME
    
    @classmethod
    def matches_url(cls, url: str) -> bool:
        """
        Check if this handler matches the given URL.
        
        Args:
            url: The job application URL
            
        Returns:
            True if this handler should be used for this URL
        """
        url_lower = url.lower()
        return any(pattern in url_lower for pattern in cls.URL_PATTERNS)
    
    @abstractmethod
    def process_page(self, page) -> WorkflowResult:
        """
        Process a single page of the application.
        
        This method should:
        1. Extract page content
        2. Analyze with AI or platform-specific logic
        3. Fill form fields
        4. Return result indicating next steps
        
        Args:
            page: Playwright page object
            
        Returns:
            WorkflowResult with processing outcome
        """
        pass
    
    @abstractmethod
    def process_application(self, page) -> WorkflowResult:
        """
        Process the entire job application flow.
        
        This method should handle:
        1. Multi-page navigation
        2. Form filling across pages
        3. CAPTCHA detection and pausing
        4. Final submission
        
        Args:
            page: Playwright page object
            
        Returns:
            WorkflowResult with final outcome
        """
        pass
    
    def can_handle_page(self, page) -> bool:
        """
        Check if this handler can process the current page.
        
        Override this method for platform-specific page detection.
        
        Args:
            page: Playwright page object
            
        Returns:
            True if this handler can process the page
        """
        return self.matches_url(page.url)
    
    def get_platform_specific_selectors(self) -> Dict[str, str]:
        """
        Return platform-specific CSS selectors for common elements.
        
        Override this method to provide optimized selectors for the platform.
        
        Returns:
            Dict mapping element names to CSS selectors
        """
        return {}
    
    def get_platform_specific_wait_times(self) -> Dict[str, int]:
        """
        Return platform-specific wait times in milliseconds.
        
        Override this method to adjust wait times for slow platforms.
        
        Returns:
            Dict mapping wait type names to milliseconds
        """
        return {
            "page_load": 10000,
            "network_idle": 10000,
            "element_visible": 5000,
            "after_click": 2000,
            "after_fill": 100,
        }
    
    def pre_process_hook(self, page) -> None:
        """
        Hook called before processing a page.
        
        Override to add platform-specific pre-processing.
        
        Args:
            page: Playwright page object
        """
        pass
    
    def post_process_hook(self, page, result: WorkflowResult) -> WorkflowResult:
        """
        Hook called after processing a page.
        
        Override to add platform-specific post-processing.
        
        Args:
            page: Playwright page object
            result: The processing result
            
        Returns:
            Modified result (or original)
        """
        return result
    
    def _log(self, message: str, level: str = "info") -> None:
        """Helper to log with job ID prefix."""
        short_id = self.job_id[:8]
        log_message = f"[{short_id}] [{self.PLATFORM_NAME}] {message}"
        
        if level == "error":
            logger.error(log_message)
            print(f"  [ERROR] {log_message}", flush=True)
        elif level == "warning":
            logger.warning(log_message)
            print(f"  [WARN] {log_message}", flush=True)
        else:
            logger.info(log_message)
            print(f"  {log_message}", flush=True)

