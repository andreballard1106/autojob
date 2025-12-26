"""
Workflow registry for managing platform-specific handlers.

This module provides a registry pattern for registering and retrieving
workflow handlers based on platform name or URL pattern detection.
"""

import logging
from typing import Dict, List, Optional, Type

from automation.workflows.base import BaseWorkflowHandler

logger = logging.getLogger(__name__)


class WorkflowRegistry:
    """
    Registry for platform-specific workflow handlers.
    
    Provides methods to:
    - Register handlers for specific platforms
    - Get handler by platform name
    - Auto-detect handler from URL
    - List all registered platforms
    """
    
    def __init__(self):
        """Initialize an empty registry."""
        self._handlers: Dict[str, Type[BaseWorkflowHandler]] = {}
        self._default_handler: Optional[Type[BaseWorkflowHandler]] = None
    
    def register(
        self,
        handler_class: Type[BaseWorkflowHandler],
        platform_name: str = None,
    ) -> None:
        """
        Register a workflow handler for a platform.
        
        Args:
            handler_class: The workflow handler class to register
            platform_name: Optional override for platform name (uses class PLATFORM_NAME if not provided)
        """
        name = platform_name or handler_class.PLATFORM_NAME
        self._handlers[name.lower()] = handler_class
        logger.info(f"Registered workflow handler: {name}")
        print(f"  [REGISTRY] Registered handler for platform: {name}")
    
    def register_default(self, handler_class: Type[BaseWorkflowHandler]) -> None:
        """
        Register the default workflow handler.
        
        This handler is used when no platform-specific handler is found.
        
        Args:
            handler_class: The default workflow handler class
        """
        self._default_handler = handler_class
        logger.info(f"Registered default workflow handler: {handler_class.PLATFORM_NAME}")
    
    def get_handler_class(self, platform: str) -> Optional[Type[BaseWorkflowHandler]]:
        """
        Get the handler class for a specific platform.
        
        Args:
            platform: Platform name (e.g., "workday", "greenhouse")
            
        Returns:
            Handler class or None if not found
        """
        return self._handlers.get(platform.lower())
    
    def get_handler_for_url(self, url: str) -> Optional[Type[BaseWorkflowHandler]]:
        """
        Auto-detect and return the appropriate handler class for a URL.
        
        Args:
            url: The job application URL
            
        Returns:
            Handler class that matches the URL, or None
        """
        for name, handler_class in self._handlers.items():
            if handler_class.matches_url(url):
                logger.info(f"URL matched handler: {name}")
                return handler_class
        return None
    
    def get_handler(
        self,
        platform: str = None,
        url: str = None,
        fallback_to_default: bool = True,
    ) -> Optional[Type[BaseWorkflowHandler]]:
        """
        Get the appropriate handler class.
        
        Resolution order:
        1. Exact platform name match
        2. URL pattern matching
        3. Default handler (if fallback_to_default=True)
        
        Args:
            platform: Platform name from AI detection (e.g., "workday")
            url: Job application URL for pattern matching
            fallback_to_default: Whether to return default handler if no match
            
        Returns:
            Handler class or None
        """
        # 1. Try exact platform match first
        if platform and platform.lower() not in ("unknown", "custom"):
            handler = self.get_handler_class(platform)
            if handler:
                logger.info(f"Found handler for platform: {platform}")
                return handler
        
        # 2. Try URL pattern matching
        if url:
            handler = self.get_handler_for_url(url)
            if handler:
                return handler
        
        # 3. Fall back to default
        if fallback_to_default and self._default_handler:
            logger.info("Using default workflow handler")
            return self._default_handler
        
        return None
    
    def create_handler(
        self,
        driver,
        ai_service,
        profile_data: dict,
        job_id: str,
        platform: str = None,
        url: str = None,
        storage=None,
        detector=None,
        notifier=None,
        app_logger=None,
    ) -> Optional[BaseWorkflowHandler]:
        """
        Create an instance of the appropriate handler.
        
        Args:
            driver: Selenium WebDriver instance
            ai_service: AIService for page analysis
            profile_data: User profile data
            job_id: Job application ID
            platform: Platform name from AI detection
            url: Job application URL
            storage: Session storage service
            detector: CAPTCHA detector
            notifier: Notification service
            app_logger: Application logger
            
        Returns:
            Instantiated handler or None
        """
        handler_class = self.get_handler(platform=platform, url=url)
        
        if not handler_class:
            logger.warning(f"No handler found for platform={platform}, url={url}")
            return None
        
        return handler_class(
            driver=driver,
            ai_service=ai_service,
            profile_data=profile_data,
            job_id=job_id,
            storage=storage,
            detector=detector,
            notifier=notifier,
            app_logger=app_logger,
        )
    
    def list_platforms(self) -> List[str]:
        """
        List all registered platform names.
        
        Returns:
            List of platform names
        """
        return list(self._handlers.keys())
    
    def has_handler(self, platform: str) -> bool:
        """
        Check if a handler is registered for a platform.
        
        Args:
            platform: Platform name
            
        Returns:
            True if handler exists
        """
        return platform.lower() in self._handlers
    
    def get_default_handler_class(self) -> Optional[Type[BaseWorkflowHandler]]:
        """Get the default handler class."""
        return self._default_handler


# Global registry instance
workflow_registry = WorkflowRegistry()

