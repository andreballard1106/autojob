"""
Platform-specific workflow handlers.

This package contains handlers optimized for specific job application platforms.

To add a new platform handler:
1. Create a new file (e.g., myplatform.py) in this directory
2. Extend BaseWorkflowHandler or DefaultWorkflowHandler
3. Set PLATFORM_NAME and URL_PATTERNS
4. Override methods as needed for platform-specific behavior
5. Add the handler class to IMPLEMENTED_HANDLERS list below

Implemented Platforms:
- Workday: Most common enterprise ATS
  - Handles job description extraction
  - Manages Start Application modal
  - Pauses for Create Account/Sign In
  - Supports multi-select with Enter key input
"""

from automation.workflows.platforms.workday import WorkdayWorkflowHandler

# List of implemented platform handlers
IMPLEMENTED_HANDLERS = [
    WorkdayWorkflowHandler,
]


def register_all_platform_handlers(registry) -> None:
    """
    Register all implemented platform handlers.
    
    Args:
        registry: The workflow registry to register handlers with
    """
    for handler_class in IMPLEMENTED_HANDLERS:
        registry.register(handler_class)
        print(f"  [PLATFORMS] Registered: {handler_class.PLATFORM_NAME}")

