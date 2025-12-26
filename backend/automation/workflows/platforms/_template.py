"""
Template for creating platform-specific workflow handlers.

Copy this file and customize for your target platform.

Steps:
1. Copy this file to a new file (e.g., workday.py)
2. Rename the class (e.g., WorkdayWorkflowHandler)
3. Set PLATFORM_NAME to match the AI detection value
4. Add URL_PATTERNS for URL-based detection
5. Override methods as needed
6. Register in the registry
"""

from typing import Dict, List

from automation.workflows.default import DefaultWorkflowHandler
from automation.workflows.base import WorkflowResult


class TemplateWorkflowHandler(DefaultWorkflowHandler):
    """
    Template platform workflow handler.
    
    Extend DefaultWorkflowHandler to inherit all default behavior,
    then override specific methods for platform optimizations.
    """
    
    # Platform identifier - must match what AI returns
    PLATFORM_NAME = "template"
    
    # URL patterns for auto-detection from URL
    URL_PATTERNS = [
        "example.com",
        "template.example.com",
    ]
    
    def get_platform_specific_selectors(self) -> Dict[str, str]:
        """
        Return platform-specific CSS selectors.
        
        Override this to provide optimized selectors for the platform.
        This can speed up element location and improve reliability.
        """
        return {
            # Common form elements
            "first_name": "#firstName, [name='firstName']",
            "last_name": "#lastName, [name='lastName']",
            "email": "#email, [name='email']",
            "phone": "#phone, [name='phone']",
            
            # File uploads
            "resume_upload": "input[type='file'][name='resume']",
            "cover_letter_upload": "input[type='file'][name='coverLetter']",
            
            # Navigation buttons
            "next_button": "button[type='submit']:has-text('Next')",
            "submit_button": "button[type='submit']:has-text('Submit')",
            "apply_button": "button:has-text('Apply')",
        }
    
    def get_platform_specific_wait_times(self) -> Dict[str, int]:
        """
        Return platform-specific wait times in milliseconds.
        
        Override for platforms with slow loading or heavy JavaScript.
        """
        return {
            "page_load": 15000,      # Max time to wait for page load
            "network_idle": 10000,   # Max time to wait for network idle
            "element_visible": 5000, # Max time to wait for element to be visible
            "after_click": 2000,     # Time to wait after clicking navigation
            "after_fill": 100,       # Time to wait after filling a field
        }
    
    def pre_process_hook(self, page) -> None:
        """
        Hook called before processing each page.
        
        Use for platform-specific setup like:
        - Closing popups/modals
        - Accepting cookies
        - Waiting for dynamic content
        """
        # Example: Close cookie banner if present
        try:
            cookie_btn = page.locator("button:has-text('Accept')").first
            if cookie_btn.is_visible(timeout=1000):
                cookie_btn.click()
                self._log("Closed cookie banner")
        except Exception:
            pass
    
    def post_process_hook(self, page, result: WorkflowResult) -> WorkflowResult:
        """
        Hook called after processing each page.
        
        Use for platform-specific cleanup or result modification.
        """
        # Example: Log platform-specific info
        self._log(f"Page processed - fields: {result.fields_filled}")
        return result
    
    def _try_click_apply_button(self, page) -> bool:
        """
        Override to provide platform-specific Apply button handling.
        
        Called when trying to start an application from a job listing page.
        """
        # Try platform-specific selectors first
        selectors = self.get_platform_specific_selectors()
        apply_selector = selectors.get("apply_button")
        
        if apply_selector:
            try:
                btn = page.locator(apply_selector).first
                if btn.is_visible():
                    btn.click()
                    self._log(f"Clicked platform-specific Apply button")
                    return True
            except Exception:
                pass
        
        # Fall back to default patterns
        return super()._try_click_apply_button(page)
    
    def _click_next_button_fallback(self, page) -> bool:
        """
        Override to provide platform-specific Next button handling.
        
        Called when AI-detected next button fails.
        """
        # Try platform-specific selectors first
        selectors = self.get_platform_specific_selectors()
        next_selector = selectors.get("next_button")
        
        if next_selector:
            try:
                btn = page.locator(next_selector).first
                if btn.is_visible():
                    btn.click()
                    self._log(f"Clicked platform-specific Next button")
                    return True
            except Exception:
                pass
        
        # Fall back to default patterns
        return super()._click_next_button_fallback(page)


# Example of a more advanced override:
# 
# def process_page(self, page) -> WorkflowResult:
#     """
#     Completely override page processing for custom behavior.
#     """
#     # Platform-specific processing logic
#     # ...
#     return WorkflowResult(success=True, ...)

