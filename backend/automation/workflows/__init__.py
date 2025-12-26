"""
Platform-specific workflow handlers for job application automation.

This module provides a modular architecture for handling different job application
platforms (Workday, Greenhouse, Lever, etc.) with platform-specific optimizations.

Usage:
    from automation.workflows import workflow_registry, DefaultWorkflowHandler
    
    # Register platform-specific handlers
    workflow_registry.register(MyWorkdayHandler)
    workflow_registry.register(MyGreenhouseHandler)
    
    # Set default handler
    workflow_registry.register_default(DefaultWorkflowHandler)
    
    # Get handler for a platform
    handler_class = workflow_registry.get_handler(platform="workday")

Implemented Platforms:
    - workday: Full workflow with job extraction, auth handling, multi-select support
"""

from automation.workflows.base import BaseWorkflowHandler, WorkflowResult
from automation.workflows.registry import WorkflowRegistry, workflow_registry
from automation.workflows.default import DefaultWorkflowHandler


def initialize_workflow_registry() -> WorkflowRegistry:
    """
    Initialize the workflow registry with default and platform-specific handlers.
    
    Call this function at application startup to set up the workflow system.
    This automatically registers all implemented platform handlers.
    
    Returns:
        The initialized workflow registry
    """
    # Register the default handler as fallback
    workflow_registry.register_default(DefaultWorkflowHandler)
    
    # Register default handler also as "default" platform
    workflow_registry.register(DefaultWorkflowHandler, "default")
    
    # Register all implemented platform-specific handlers
    from automation.workflows.platforms import register_all_platform_handlers
    register_all_platform_handlers(workflow_registry)
    
    print(f"  [WORKFLOWS] Initialized with default handler")
    print(f"  [WORKFLOWS] Registered platforms: {workflow_registry.list_platforms()}")
    
    return workflow_registry


# List of known platforms for reference
KNOWN_PLATFORMS = [
    "workday",      # Oracle Cloud HCM / Workday
    "greenhouse",   # Greenhouse ATS
    "lever",        # Lever ATS
    "workable",     # Workable ATS
    "smartrecruiters",  # SmartRecruiters
    "icims",        # iCIMS
    "taleo",        # Oracle Taleo
    "successfactors",  # SAP SuccessFactors
    "jobvite",      # Jobvite
    "bamboohr",     # BambooHR
    "ashbyhq",      # Ashby HQ
    "custom",       # Custom company system
    "unknown",      # Unknown platform
]


__all__ = [
    "BaseWorkflowHandler",
    "WorkflowResult",
    "WorkflowRegistry",
    "workflow_registry",
    "DefaultWorkflowHandler",
    "initialize_workflow_registry",
    "KNOWN_PLATFORMS",
]

