"""
Workday Platform Workflow Handler

This module implements a specialized workflow handler for Workday job applications.
Workday is one of the most common ATS platforms used by large enterprises.

Workflow Steps:
1. Extract job description from job listing page
2. Click Apply button to start application
3. Handle "Start Your Application" modal - click "Apply manually"
4. Detect Create Account/Sign In page and pause for user action
5. Monitor for My Information page (user completed auth)
6. Resume auto-fill for multi-page application form
7. Handle multi-select components with Enter key for each value
8. Navigate through Save and Continue until Submit
"""

import json
import logging
import re
import time
import traceback
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple

from automation.workflows.base import BaseWorkflowHandler, WorkflowResult
from automation.page_analyzer import PageAnalyzer, PageContent
from automation.captcha_detector import CaptchaDetectionResult
from automation.application_logger import LogAction
from autofill import AutofillEngine
from autofill.models import FillResult

logger = logging.getLogger(__name__)

# Maximum pages to process in multi-page Workday application
MAX_WORKDAY_PAGES = 15

# Workday-specific page step identifiers
WORKDAY_STEP_PATTERNS = {
    "job_listing": [
        "jobPostingPage",
        "job-posting",
        "job/",
        "/job/"
    ],
    "start_application_modal": [
        "Start Your Application",
        "Apply manually",
        "Use my last application",
    ],
    "create_account": [
        "Create Account",
        "Sign In",
        "signIn",
        "createAccount",
        "Log In",
        "existing-user",
        "new-user",
    ],
    "my_information": [
        "My Information",
        "myInformation",
        "legalNameSection",
        "contactInformationSection",
    ],
    "my_experience": [
        "My Experience",
        "myExperience",
        "workExperience",
        "education",
    ],
    "application_questions": [
        "Application Questions",
        "additionalQuestions",
        "customQuestions",
    ],
    "voluntary_disclosures": [
        "Voluntary Disclosures",
        "voluntaryDisclosures",
        "EEO",
        "selfIdentification",
    ],
    "review": [
        "Review",
        "reviewPage",
        "applicationReview",
    ],
}


@dataclass
class WorkdayJobInfo:
    """Stores extracted job information for use in form filling."""
    job_title: str = ""
    company_name: str = ""
    job_description: str = ""
    location: str = ""
    job_type: str = ""
    salary_range: str = ""
    requirements: List[str] = field(default_factory=list)
    responsibilities: List[str] = field(default_factory=list)
    qualifications: List[str] = field(default_factory=list)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "job_title": self.job_title,
            "company_name": self.company_name,
            "job_description": self.job_description,
            "location": self.location,
            "job_type": self.job_type,
            "salary_range": self.salary_range,
            "requirements": self.requirements,
            "responsibilities": self.responsibilities,
            "qualifications": self.qualifications,
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "WorkdayJobInfo":
        return cls(
            job_title=data.get("job_title", ""),
            company_name=data.get("company_name", ""),
            job_description=data.get("job_description", ""),
            location=data.get("location", ""),
            job_type=data.get("job_type", ""),
            salary_range=data.get("salary_range", ""),
            requirements=data.get("requirements", []),
            responsibilities=data.get("responsibilities", []),
            qualifications=data.get("qualifications", []),
        )


class WorkdayWorkflowHandler(BaseWorkflowHandler):
    """
    Specialized workflow handler for Workday job applications.
    
    Features:
    - Extracts full job description before applying
    - Handles "Apply manually" flow
    - Detects and pauses on Create Account/Sign In
    - Monitors for auth completion and resumes
    - Handles multi-select components with API-loaded options
    - Supports Enter key input for multi-select values
    """
    
    PLATFORM_NAME = "workday"
    
    # URL patterns for Workday detection
    URL_PATTERNS = [
        "myworkdayjobs.com",
        "myworkdaysite.com",
        "workday.com/",
        "wd1.myworkdaysite",
        "wd2.myworkdaysite",
        "wd3.myworkdaysite",
        "wd5.myworkdaysite",
        ".wd1.myworkdayjobs",
        ".wd3.myworkdayjobs",
        ".wd5.myworkdayjobs",
    ]
    
    # Workday-specific data-automation-id selectors
    WORKDAY_SELECTORS = {
        # Job listing page
        "apply_button": "[data-automation-id='jobPostingApplyButton']",
        "job_title": "[data-automation-id='jobPostingHeader'] h2, [data-automation-id='jobTitle']",
        "job_description": "[data-automation-id='jobPostingDescription'], [data-automation-id='jobDescription']",
        "company_name": "[data-automation-id='companyName'], [data-automation-id='organizationName']",
        
        # Start application modal
        "apply_manually_button": "[data-automation-id='applyManually'], button:has-text('Apply manually')",
        "use_last_application": "[data-automation-id='useMyLastApplication']",
        
        # Create Account / Sign In
        "sign_in_section": "[data-automation-id='signInSection'], [data-automation-id='existingUser']",
        "create_account_section": "[data-automation-id='createAccountSection'], [data-automation-id='newUser']",
        "sign_in_button": "[data-automation-id='signInLink'], button:has-text('Sign In')",
        "create_account_button": "[data-automation-id='createAccountLink'], button:has-text('Create Account')",
        
        # Form elements
        "first_name": "[data-automation-id='legalNameSection_firstName']",
        "last_name": "[data-automation-id='legalNameSection_lastName']",
        "email": "[data-automation-id='email']",
        "phone_device_type": "[data-automation-id='phone-device-type']",
        "phone_number": "[data-automation-id='phone-number']",
        "address_line1": "[data-automation-id='addressSection_addressLine1']",
        "city": "[data-automation-id='addressSection_city']",
        "state": "[data-automation-id='addressSection_countryRegion']",
        "postal_code": "[data-automation-id='addressSection_postalCode']",
        "country": "[data-automation-id='addressSection_country']",
        
        # File uploads
        "resume_upload": "[data-automation-id='file-upload-input-ref']",
        "resume_dropzone": "[data-automation-id='file-upload-drop-zone']",
        
        # Navigation buttons
        "save_and_continue": "[data-automation-id='bottom-navigation-next-button']",
        "submit_button": "[data-automation-id='bottom-navigation-next-button']:has-text('Submit')",
        "back_button": "[data-automation-id='bottom-navigation-previous-button']",
        
        # Progress indicator
        "progress_bar": "[data-automation-id='progressBar']",
        "current_step": "[data-automation-id='currentStep']",
        
        # Multi-select / Dropdown
        "multi_select_input": "[data-automation-id='multiselectInputContainer'] input",
        "dropdown_input": "[data-automation-id='selectInputContainer'] input",
        "dropdown_option": "[data-automation-id='promptOption']",
    }
    
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
        super().__init__(
            driver=driver,
            ai_service=ai_service,
            profile_data=profile_data,
            job_id=job_id,
            storage=storage,
            detector=detector,
            notifier=notifier,
            app_logger=app_logger,
        )
        
        self.autofill_engine = AutofillEngine(driver)
        self.page_analyzer = PageAnalyzer()
        
        # Workday-specific state
        self._job_info: Optional[WorkdayJobInfo] = None
        self._current_step: str = "unknown"
        self._auth_required: bool = False
        self._waiting_for_auth: bool = False
        
        # Configure autofill engine
        self.autofill_engine.configure(
            stop_on_error=False,
            retry_count=1,  # One retry for Workday's dynamic elements
            retry_delay_ms=500,
        )
    
    def get_platform_specific_selectors(self) -> Dict[str, str]:
        """Return Workday-specific CSS selectors."""
        return self.WORKDAY_SELECTORS
    
    def get_platform_specific_wait_times(self) -> Dict[str, int]:
        """Return Workday-specific wait times (Workday pages load slowly)."""
        return {
            "page_load": 20000,
            "network_idle": 15000,
            "element_visible": 10000,
            "after_click": 3000,
            "after_fill": 200,
            "modal_appear": 5000,
        }
    
    # =========================================================================
    # Main Entry Points
    # =========================================================================
    
    def process_page(self, page) -> WorkflowResult:
        """Process a single Workday page."""
        try:
            self.pre_process_hook(page)
            result = self._process_page_internal(page)
            return self.post_process_hook(page, result)
        except Exception as e:
            self._log(f"Error processing page: {e}", "error")
            traceback.print_exc()
            return WorkflowResult(
                success=False,
                error=f"Workday page processing error: {str(e)}",
                platform=self.PLATFORM_NAME,
            )
    
    def process_application(self, page) -> WorkflowResult:
        """Process entire Workday job application flow."""
        try:
            return self._process_application_internal(page)
        except Exception as e:
            self._log(f"Error processing application: {e}", "error")
            traceback.print_exc()
            if self.storage:
                self.storage.set_session_status(self.job_id, "error", str(e))
            return WorkflowResult(
                success=False,
                error=f"Workday application error: {str(e)}",
                platform=self.PLATFORM_NAME,
            )
    
    # =========================================================================
    # Application Flow Implementation
    # =========================================================================
    
    def _process_application_internal(self, page) -> WorkflowResult:
        """
        Main Workday application workflow:
        
        CORRECT FLOW - WHEN PAGE OPENS:
        1. Extract page HTML content IMMEDIATELY
        2. Filter HTML content
        3. Send filtered content to OpenAI
        4. Receive job description + apply button selector from AI
        5. Store job description in session
        6. Click Apply button
        
        THEN CONTINUE WITH:
        7. Handle Start Application modal
        8. Detect auth requirement and pause/wait
        9. Process multi-page form
        """
        self._log("="*60)
        self._log("STARTING WORKDAY APPLICATION WORKFLOW")
        self._log("="*60)
        
        # Initialize session
        if self.storage:
            session = self.storage.get_session(self.job_id)
            if not session:
                self.storage.create_session(
                    job_id=self.job_id,
                    profile_id=self.profile_data.get("id", ""),
                    url=page.url,
                )
        
        if self.app_logger:
            self.app_logger.log_sync(
                job_id=self.job_id,
                action=LogAction.PROCESSING_STARTED,
                details={
                    "url": page.url,
                    "platform": "workday",
                    "profile_id": self.profile_data.get("id", ""),
                },
            )
        
        current_url = page.url
        
        # ============================================
        # STEP 1: IMMEDIATELY Extract page HTML content (FIRST THING TO DO!)
        # ============================================
        self._log("STEP 1: Extracting page HTML content IMMEDIATELY...")
        page_content = self._extract_page_content(page)
        self._log(f"  Extracted: {len(page_content.filtered_html)} chars of filtered HTML")
        self._log(f"  Found {len(page_content.inputs)} inputs, {len(page_content.buttons)} buttons")
        
        # Save page snapshot
        if self.storage:
            self.storage.add_page_snapshot(self.job_id, page_content.to_dict())
        
        # ============================================
        # STEP 2: Send filtered HTML to OpenAI for analysis
        # ============================================
        self._log("STEP 2: Sending filtered HTML to OpenAI...")
        job_info, apply_button_selector = self._extract_job_info_from_ai(page_content)
        
        # ============================================
        # STEP 3: Store job description in session
        # ============================================
        if job_info:
            self._job_info = job_info
            self._log("STEP 3: Storing job description in session...")
            self._store_job_info(job_info)
            self._log(f"  Job Title: {job_info.job_title}")
            self._log(f"  Company: {job_info.company_name}")
            self._log(f"  Description length: {len(job_info.job_description)} chars")
        else:
            self._log("STEP 3: WARNING - Could not extract job description from AI", "warning")
        
        # ============================================
        # STEP 4: Click Apply button (using AI-provided selector)
        # ============================================
        self._log("STEP 4: Clicking Apply button...")
        apply_clicked = self._click_apply_button(page, apply_button_selector)
        if not apply_clicked:
            return WorkflowResult(
                success=False,
                error="Could not find or click Apply button",
                platform=self.PLATFORM_NAME,
            )
        
        # Wait for next page/modal
        time.sleep(2)
        self._wait_for_page_load(page)
        
        # Now detect page type AFTER clicking Apply (for subsequent steps)
        page_type = self._detect_workday_page_type(page)
        self._log(f"After Apply click, page type: {page_type}")
        
        # ============================================
        # STEP 3: Handle Start Application Modal
        # ============================================
        if page_type == "start_application_modal" or self._has_start_application_modal(page):
            self._log("Handling Start Application modal...")
            
            modal_handled = self._handle_start_application_modal(page)
            if not modal_handled:
                self._log("Could not handle Start Application modal", "warning")
            
            # Wait for next page
            time.sleep(2)
            self._wait_for_page_load(page)
            
            # Re-detect page type
            page_type = self._detect_workday_page_type(page)
            self._log(f"After modal, page type: {page_type}")
        
        # ============================================
        # STEP 4: Handle Create Account/Sign In
        # ============================================
        if page_type == "create_account":
            self._log("Create Account/Sign In page detected - PAUSING FOR USER ACTION")
            
            self._auth_required = True
            self._waiting_for_auth = True
            
            # Notify user
            if self.notifier:
                self.notifier.notify_action_required(
                    job_id=self.job_id,
                    action_type="Authentication Required",
                    message="Please create an account or sign in to continue with the Workday application.",
                    profile_id=self.profile_data.get("id"),
                )
            
            # Update session status
            if self.storage:
                self.storage.set_session_status(
                    self.job_id,
                    "awaiting_auth",
                    "Create Account/Sign In required. Please complete authentication.",
                )
            
            if self.app_logger:
                self.app_logger.log_sync(
                    job_id=self.job_id,
                    action=LogAction.USER_ACTION_REQUIRED,
                    details={
                        "action_type": "authentication",
                        "page_type": "create_account",
                        "url": page.url,
                    },
                )
            
            # Return paused result
            return WorkflowResult(
                success=True,
                page_number=1,
                needs_more_navigation=True,
                submit_ready=False,
                paused=True,
                pause_reason="Create Account/Sign In required. Please complete authentication to continue.",
                platform=self.PLATFORM_NAME,
            )
        
        # ============================================
        # STEP 5: Process Multi-Page Application Form
        # ============================================
        # At this point we should be on My Information or another form page
        return self._process_workday_form_pages(page)
    
    def _process_workday_form_pages(self, page) -> WorkflowResult:
        """Process the multi-page Workday application form."""
        self._log("Starting multi-page form processing...")
        
        total_filled = 0
        total_failed = 0
        all_unmapped = []
        processed_pages = set()
        
        for page_num in range(MAX_WORKDAY_PAGES):
            current_url = page.url
            page_type = self._detect_workday_page_type(page)
            
            # Create page signature
            try:
                page_title = page.title if hasattr(page, 'title') else ""
                if callable(page_title):
                    page_title = page_title()
                step_indicator = self._get_current_step_indicator(page)
                page_signature = f"{page_type}_{step_indicator}"
            except Exception:
                page_signature = f"{page_type}_unknown"
            
            page_key = (current_url, page_signature)
            
            # Check for duplicate processing
            if page_key in processed_pages:
                self._log(f"Page already processed: {page_signature}")
                break
            
            self._log(f"\n=== WORKDAY PAGE {page_num + 1}: {page_type} ===")
            self._log(f"URL: {current_url[:60]}...")
            
            processed_pages.add(page_key)
            
            # Log page load
            if self.app_logger:
                self.app_logger.log_sync(
                    job_id=self.job_id,
                    action=LogAction.PAGE_LOADED,
                    details={
                        "url": current_url,
                        "page_type": page_type,
                        "page_number": page_num + 1,
                    },
                )
            
            # Check for CAPTCHA
            captcha_result = self._check_for_captcha(page)
            if captcha_result.detected:
                self._log(f"CAPTCHA detected: {captcha_result.captcha_type}")
                return self._handle_captcha_pause(
                    page, captcha_result, total_filled, total_failed,
                    page_num + 1, all_unmapped
                )
            
            # Check if this is a Create Account page (user returned to it)
            if page_type == "create_account":
                return WorkflowResult(
                    success=True,
                    page_number=page_num + 1,
                    fields_filled=total_filled,
                    fields_failed=total_failed,
                    paused=True,
                    pause_reason="Authentication required. Please sign in or create account.",
                    platform=self.PLATFORM_NAME,
                )
            
            # Check if this is the review/submit page
            if page_type == "review":
                self._log("Review page reached - ready for submission")
                if self.storage:
                    self.storage.set_session_status(self.job_id, "ready_to_submit")
                
                return WorkflowResult(
                    success=True,
                    page_number=page_num + 1,
                    fields_filled=total_filled,
                    fields_failed=total_failed,
                    needs_more_navigation=False,
                    submit_ready=True,
                    unmapped_fields=all_unmapped,
                    platform=self.PLATFORM_NAME,
                )
            
            # Process the current form page
            result = self._process_workday_form_page(page, page_type)
            
            total_filled += result.fields_filled
            total_failed += result.fields_failed
            all_unmapped.extend(result.unmapped_fields or [])
            
            # Check for errors
            if result.error and not result.success:
                self._log(f"Page processing error: {result.error}", "error")
                return result
            
            # Check if submit ready
            if result.submit_ready:
                self._log(f"Application ready for submission! Total filled: {total_filled}")
                return WorkflowResult(
                    success=True,
                    page_number=page_num + 1,
                    fields_filled=total_filled,
                    fields_failed=total_failed,
                    submit_ready=True,
                    unmapped_fields=all_unmapped,
                    platform=self.PLATFORM_NAME,
                )
            
            # Click Save and Continue
            if result.needs_more_navigation:
                nav_clicked = self._click_save_and_continue(page)
                
                if nav_clicked:
                    self._log("Clicked Save and Continue, waiting for next page...")
                    time.sleep(2)
                    self._wait_for_page_load(page)
                    continue
                else:
                    self._log("Could not click navigation button", "warning")
                    break
            else:
                self._log("No more navigation needed")
                break
        
        # Final status
        final_status = "completed" if total_filled > 0 else "incomplete"
        if self.storage:
            self.storage.set_session_status(self.job_id, final_status)
        
        self._log(f"\nWorkday form processing complete. Total: {total_filled} filled, {total_failed} failed")
        
        return WorkflowResult(
            success=total_filled > 0,
            page_number=page_num + 1,
            fields_filled=total_filled,
            fields_failed=total_failed,
            unmapped_fields=all_unmapped,
            platform=self.PLATFORM_NAME,
        )
    
    def _process_workday_form_page(self, page, page_type: str) -> WorkflowResult:
        """Process a single Workday form page."""
        self._log(f"Processing Workday form page: {page_type}")
        
        # Extract page content
        page_content = self._extract_page_content(page)
        
        # Save page snapshot
        if self.storage:
            self.storage.add_page_snapshot(self.job_id, page_content.to_dict())
        
        # Build prompt with job description context
        ai_response = self._analyze_workday_page(page_content)
        
        if not ai_response:
            return WorkflowResult(
                success=False,
                error="AI analysis failed",
                platform=self.PLATFORM_NAME,
            )
        
        # Execute autofill commands
        filled = 0
        failed = 0
        results = []
        
        if ai_response.field_mappings:
            results, filled, failed = self._execute_workday_autofill(
                page, ai_response.field_mappings
            )
            self._save_autofill_results(results, ai_response)
        
        # Determine navigation
        has_next = self._has_save_and_continue(page)
        is_submit = self._is_submit_button(page)
        
        return WorkflowResult(
            success=filled > 0 or failed == 0,
            fields_filled=filled,
            fields_failed=failed,
            needs_more_navigation=has_next and not is_submit,
            submit_ready=is_submit,
            unmapped_fields=ai_response.unmapped_fields if ai_response else [],
            platform=self.PLATFORM_NAME,
        )
    
    def _process_page_internal(self, page) -> WorkflowResult:
        """Process single page for process_page() entry point."""
        page_type = self._detect_workday_page_type(page)
        return self._process_workday_form_page(page, page_type)
    
    # =========================================================================
    # Job Description Extraction (from filtered HTML via OpenAI)
    # =========================================================================
    
    def _extract_job_info_from_ai(
        self,
        page_content: PageContent
    ) -> Tuple[Optional[WorkdayJobInfo], Optional[str]]:
        """
        Extract job information from filtered HTML content using AI.
        
        This is the main method for job listing page processing:
        1. Takes already-extracted and filtered page content
        2. Sends to OpenAI for analysis
        3. Returns job description AND apply button selector
        
        Args:
            page_content: Pre-extracted and filtered page content
            
        Returns:
            Tuple of (WorkdayJobInfo, apply_button_selector)
        """
        self._log("Sending filtered HTML to OpenAI for job extraction...")
        
        try:
            # Check AI service availability
            if not self.ai_service or not self.ai_service.client:
                self._log("AI service not available", "warning")
                return None, None
            
            # Build the prompt with filtered HTML content
            prompt = self._build_job_extraction_prompt(page_content)
            
            self._log(f"  Prompt size: {len(prompt)} chars")
            self._log(f"  Filtered HTML size: {len(page_content.filtered_html)} chars")
            
            # Call OpenAI
            response = self.ai_service.client.chat.completions.create(
                model=self.ai_service.model,
                messages=[
                    {"role": "system", "content": self._get_job_extraction_system_prompt()},
                    {"role": "user", "content": prompt},
                ],
                temperature=0.1,
                max_tokens=3000,
            )
            
            content = response.choices[0].message.content
            self._log(f"  Received AI response: {len(content)} chars")
            
            # Parse the response
            job_data = self._parse_job_extraction_response(content)
            
            if job_data:
                job_info = WorkdayJobInfo.from_dict(job_data)
                apply_button_selector = job_data.get("apply_button_selector")
                
                self._log(f"  Extracted job title: {job_info.job_title[:50] if job_info.job_title else 'N/A'}")
                self._log(f"  Apply button selector: {apply_button_selector[:50] if apply_button_selector else 'N/A'}")
                
                return job_info, apply_button_selector
            
            self._log("Failed to parse AI response", "warning")
            return None, None
            
        except Exception as e:
            self._log(f"Error in AI job extraction: {e}", "error")
            traceback.print_exc()
            return None, None
    
    def _build_job_extraction_prompt(self, page_content: PageContent) -> str:
        """Build prompt for job description extraction from filtered HTML."""
        # Format buttons for AI to identify Apply button
        buttons_info = ""
        if page_content.buttons:
            buttons_info = "\n=== BUTTONS ON PAGE ===\n"
            for i, btn in enumerate(page_content.buttons[:20]):
                btn_text = btn.get('text', '')[:50]
                btn_id = btn.get('data-automation-id', '') or btn.get('id', '')
                buttons_info += f"{i+1}. text='{btn_text}' data-automation-id='{btn_id}'\n"
        
        return f"""
Analyze this Workday job listing page HTML content and extract:
1. Full job description and details
2. The CSS selector for the Apply button

=== PAGE INFO ===
URL: {page_content.url}
Title: {page_content.title}
{buttons_info}
=== FILTERED HTML CONTENT ===
{page_content.filtered_html[:20000]}

=== INSTRUCTIONS ===
1. Extract all job information from the HTML
2. Find the Apply button and provide its CSS selector
3. For the apply_button_selector, use data-automation-id if available:
   - Preferred: [data-automation-id='jobPostingApplyButton']
   - Or use other identifiable selectors like button id, class, or text

Return ONLY valid JSON with this exact structure:
{{
    "job_title": "The job title/position name",
    "company_name": "The company name",
    "job_description": "Full job description text (can be long)",
    "location": "Job location",
    "job_type": "Full-time, Part-time, Contract, etc.",
    "salary_range": "Salary if mentioned, otherwise empty string",
    "requirements": ["requirement 1", "requirement 2"],
    "responsibilities": ["responsibility 1", "responsibility 2"],
    "qualifications": ["qualification 1", "qualification 2"],
    "apply_button_selector": "CSS selector for Apply button"
}}
"""
    
    def _get_job_extraction_system_prompt(self) -> str:
        """System prompt for job extraction from HTML."""
        return """You are an AI that extracts job information from Workday job listing page HTML.

Your task:
1. Parse the filtered HTML content to extract job details
2. Identify the Apply button and provide its CSS selector

IMPORTANT RULES:
- Extract the FULL job description, not just a summary
- For apply_button_selector, prioritize data-automation-id attributes
- Common Workday Apply button selectors:
  * [data-automation-id='jobPostingApplyButton']
  * button[data-automation-id='applyButton']
  * If not found, use text-based selector like: button:has-text('Apply')

Return ONLY valid JSON. No markdown code blocks, no explanations.
"""
    
    def _parse_job_extraction_response(self, content: str) -> Optional[Dict]:
        """Parse AI response for job extraction."""
        try:
            content = content.strip()
            if content.startswith("```"):
                content = re.sub(r'^```(?:json)?\s*', '', content)
                content = re.sub(r'\s*```$', '', content)
            return json.loads(content)
        except Exception as e:
            self._log(f"Failed to parse job extraction response: {e}", "warning")
            return None
    
    def _store_job_info(self, job_info: WorkdayJobInfo) -> None:
        """Store job info for later use in form filling."""
        if self.storage:
            self.storage.set_session_metadata(
                self.job_id,
                'workday_job_info',
                job_info.to_dict()
            )
            self.storage.set_session_platform(self.job_id, self.PLATFORM_NAME)
    
    def _get_stored_job_info(self) -> Optional[WorkdayJobInfo]:
        """Retrieve stored job info."""
        if self._job_info:
            return self._job_info
        
        if self.storage:
            job_data = self.storage.get_session_metadata(
                self.job_id,
                'workday_job_info'
            )
            if job_data:
                self._job_info = WorkdayJobInfo.from_dict(job_data)
                return self._job_info
        return None
    
    # =========================================================================
    # Page Type Detection
    # =========================================================================
    
    def _detect_workday_page_type(self, page) -> str:
        """Detect the current Workday page type."""
        try:
            url = page.url.lower()
            html_content = page.content().lower() if hasattr(page, 'content') else ""
            
            # Check URL patterns first
            if "/job/" in url or "jobposting" in url:
                # Check if there's an Apply button visible
                try:
                    apply_btn = page.locator(self.WORKDAY_SELECTORS["apply_button"]).first
                    if apply_btn.is_visible():
                        return "job_listing"
                except Exception:
                    pass
            
            # Check for Start Application modal
            if self._has_start_application_modal(page):
                return "start_application_modal"
            
            # Check for Create Account/Sign In
            for pattern in WORKDAY_STEP_PATTERNS["create_account"]:
                if pattern.lower() in html_content:
                    # Verify it's the main content, not just a link
                    try:
                        sign_in = page.locator(self.WORKDAY_SELECTORS["sign_in_section"]).first
                        create = page.locator(self.WORKDAY_SELECTORS["create_account_section"]).first
                        if sign_in.is_visible() or create.is_visible():
                            return "create_account"
                    except Exception:
                        pass
            
            # Check for My Information
            for pattern in WORKDAY_STEP_PATTERNS["my_information"]:
                if pattern.lower() in html_content:
                    return "my_information"
            
            # Check for My Experience
            for pattern in WORKDAY_STEP_PATTERNS["my_experience"]:
                if pattern.lower() in html_content:
                    return "my_experience"
            
            # Check for Application Questions
            for pattern in WORKDAY_STEP_PATTERNS["application_questions"]:
                if pattern.lower() in html_content:
                    return "application_questions"
            
            # Check for Voluntary Disclosures
            for pattern in WORKDAY_STEP_PATTERNS["voluntary_disclosures"]:
                if pattern.lower() in html_content:
                    return "voluntary_disclosures"
            
            # Check for Review page
            for pattern in WORKDAY_STEP_PATTERNS["review"]:
                if pattern.lower() in html_content:
                    return "review"
            
            # Check if it's a form page (has form inputs)
            try:
                inputs = page.locator("input:visible, select:visible, textarea:visible")
                if inputs.count() > 0:
                    return "form_page"
            except Exception:
                pass
            
            return "unknown"
            
        except Exception as e:
            self._log(f"Error detecting page type: {e}", "error")
            return "unknown"
    
    def _has_start_application_modal(self, page) -> bool:
        """Check if Start Your Application modal is visible."""
        try:
            # Check for modal content
            modal_patterns = [
                "text='Start Your Application'",
                "text='Apply manually'",
                "text='Use my last application'",
                "[data-automation-id='applyManually']",
                "[data-automation-id='useMyLastApplication']",
            ]
            
            for pattern in modal_patterns:
                try:
                    el = page.locator(pattern).first
                    if el.is_visible():
                        return True
                except Exception:
                    continue
            
            return False
            
        except Exception:
            return False
    
    def _get_current_step_indicator(self, page) -> str:
        """Get the current step from Workday's progress indicator."""
        try:
            # Try to get step from progress bar
            progress = page.locator(self.WORKDAY_SELECTORS["progress_bar"]).first
            if progress.is_visible():
                return progress.text_content().strip()[:50]
        except Exception:
            pass
        
        return "unknown"
    
    # =========================================================================
    # Navigation Actions
    # =========================================================================
    
    def _click_apply_button(self, page, ai_provided_selector: Optional[str] = None) -> bool:
        """
        Click the Apply button on job listing page.
        
        Args:
            page: Browser page object
            ai_provided_selector: Optional selector from AI analysis (priority)
        """
        self._log("Clicking Apply button...")
        
        # Build list of selectors to try (AI-provided first if available)
        selectors = []
        
        # Add AI-provided selector first (highest priority)
        if ai_provided_selector:
            selectors.append(ai_provided_selector)
            self._log(f"  AI provided selector: {ai_provided_selector[:50]}")
        
        # Add Workday-specific selectors as fallback
        selectors.extend([
            self.WORKDAY_SELECTORS["apply_button"],
            "[data-automation-id='jobPostingApplyButton']",
            "button:has-text('Apply')",
            "a:has-text('Apply')",
            "button:has-text('Apply Now')",
            "[data-automation-id='applyButton']",
        ])
        
        for selector in selectors:
            try:
                btn = page.locator(selector).first
                if btn.is_visible():
                    btn.click()
                    self._log(f"  Clicked Apply button: {selector[:40]}")
                    return True
            except Exception:
                continue
        
        self._log("Could not find Apply button", "warning")
        return False
    
    def _handle_start_application_modal(self, page) -> bool:
        """Handle the Start Your Application modal - click Apply manually."""
        self._log("Handling Start Application modal...")
        
        # Try to click "Apply manually" button
        apply_manually_selectors = [
            "[data-automation-id='applyManually']",
            "button:has-text('Apply manually')",
            "text='Apply manually'",
        ]
        
        for selector in apply_manually_selectors:
            try:
                btn = page.locator(selector).first
                if btn.is_visible():
                    btn.click()
                    self._log("Clicked 'Apply manually' button")
                    return True
            except Exception:
                continue
        
        # If no Apply manually, try clicking into the modal to continue
        self._log("Could not find 'Apply manually' button", "warning")
        return False
    
    def _click_save_and_continue(self, page) -> bool:
        """Click Save and Continue button."""
        self._log("Clicking Save and Continue...")
        
        selectors = [
            self.WORKDAY_SELECTORS["save_and_continue"],
            "button:has-text('Save and Continue')",
            "button:has-text('Continue')",
            "button:has-text('Next')",
            "[data-automation-id='bottom-navigation-next-button']",
        ]
        
        for selector in selectors:
            try:
                btn = page.locator(selector).first
                if btn.is_visible():
                    # Check if it's a Submit button
                    btn_text = btn.text_content().strip().lower()
                    btn.click()
                    self._log(f"Clicked navigation button: {btn_text}")
                    return True
            except Exception:
                continue
        
        return False
    
    def _has_save_and_continue(self, page) -> bool:
        """Check if Save and Continue button exists."""
        try:
            btn = page.locator(self.WORKDAY_SELECTORS["save_and_continue"]).first
            return btn.is_visible()
        except Exception:
            return False
    
    def _is_submit_button(self, page) -> bool:
        """Check if the navigation button is Submit (final step)."""
        try:
            btn = page.locator(self.WORKDAY_SELECTORS["save_and_continue"]).first
            if btn.is_visible():
                text = btn.text_content().strip().lower()
                return "submit" in text
        except Exception:
            pass
        return False
    
    # =========================================================================
    # Form Analysis and Filling
    # =========================================================================
    
    def _analyze_workday_page(self, page_content: PageContent):
        """Analyze Workday page with job context."""
        job_info = self._get_stored_job_info()
        
        # Build enhanced prompt with job context
        prompt = self._build_workday_form_prompt(page_content, job_info)
        
        if not self.ai_service or not self.ai_service.client:
            self._log("AI service not available", "warning")
            return None
        
        try:
            response = self.ai_service.client.chat.completions.create(
                model=self.ai_service.model,
                messages=[
                    {"role": "system", "content": self._get_workday_form_system_prompt()},
                    {"role": "user", "content": prompt},
                ],
                temperature=0.1,
                max_tokens=4000,
            )
            
            content = response.choices[0].message.content
            return self._parse_form_analysis_response(content)
            
        except Exception as e:
            self._log(f"AI analysis error: {e}", "error")
            return None
    
    def _build_workday_form_prompt(
        self,
        page_content: PageContent,
        job_info: Optional[WorkdayJobInfo]
    ) -> str:
        """Build prompt for Workday form analysis."""
        job_context = ""
        if job_info:
            job_context = f"""
=== JOB CONTEXT (Use this to answer job-related questions) ===
Job Title: {job_info.job_title}
Company: {job_info.company_name}
Location: {job_info.location}
Job Type: {job_info.job_type}
Description: {job_info.job_description[:2000] if job_info.job_description else 'N/A'}
Requirements: {', '.join(job_info.requirements[:5]) if job_info.requirements else 'N/A'}
"""
        
        profile_data = self._format_profile_for_prompt()
        
        return f"""
Analyze this Workday application form page and generate autofill commands.

{job_context}

=== USER PROFILE ===
{profile_data}

=== PAGE CONTENT ===
URL: {page_content.url}
Title: {page_content.title}

=== FORM INPUTS ===
{self._format_inputs_for_prompt(page_content.inputs)}

=== BUTTONS ===
{self._format_buttons_for_prompt(page_content.buttons)}

=== CRITICAL: IDENTIFY ALL DROPDOWN/SELECT FIELDS ===

Look for these field types in the input list:
1. **[HTML SELECT]** → tag='select' with options list → Action: "select_option"
2. **[WORKDAY DROPDOWN]** → tag='workday_dropdown' → Action: "workday_searchable_select"

THESE ARE USUALLY REQUIRED FIELDS - DO NOT SKIP THEM!

=== WORKDAY-SPECIFIC INSTRUCTIONS ===

1. **HTML SELECT ELEMENTS** (tag='select'):
   - Marked as: [HTML SELECT - USE select_option ACTION]
   - Has visible options like options=['Select One', 'Alabama', 'Alaska'...]
   - Action: "select_option"
   - Value: EXACT text from options list
   - Common fields: State, Country, Phone Type, etc.

2. **WORKDAY SEARCH-AND-SELECT / CUSTOM DROPDOWNS** (tag='workday_dropdown'):
   - Marked as: [WORKDAY DROPDOWN - USE workday_searchable_select ACTION]
   - NO visible options (options are loaded dynamically via API when user types)
   - Action: "workday_searchable_select"
   - Value: Search term to type (e.g., "LinkedIn", "California", "United States of America")
   - HOW IT WORKS:
     * System types the value → presses Enter to search → waits for options → selects matching option
   - Common fields: "How did you hear about us?", State, Country, Location, etc.
   
3. **MULTI-SELECT COMPONENTS** (search-and-select with multiple values):
   - Action: "workday_multiselect"
   - Value: ARRAY of strings ["Value1", "Value2"]
   - For EACH value: type → Enter to search → wait → Enter to select
   - Example: "How did you hear about us?" → ["LinkedIn"]
   - Example: "Skills" → ["Python", "JavaScript", "SQL"]

4. **SEARCHABLE SINGLE-SELECT** (type-to-search dropdowns):
   - Action: "workday_searchable_select"  
   - Value: Single string to search and select
   - System will: type value → Enter to search → wait → click or Enter to select
   - Example: Country field with value "United States of America"

5. CHECKBOXES:
   - Action: "workday_checkbox"
   - Value: true or false

6. RADIO BUTTONS:
   - Action: "workday_radio"
   - Value: Text of option to select

7. TEXT INPUTS:
   - Action: "type_text"
   - Use profile data

8. FILE UPLOADS:
   - Action: "upload_file"
   - file_path from profile's resume_path

=== REQUIRED FIELDS (marked with *) ===
All required fields MUST have a value!

=== OUTPUT FORMAT ===
Return JSON with:
- field_mappings: Array of autofill commands
- unmapped_fields: Fields that couldn't be mapped

For each field_mapping:
{{
    "action": "type_text|select_option|workday_multiselect|workday_searchable_select|workday_checkbox|workday_radio|upload_file",
    "selector": "CSS selector (prefer data-automation-id, or use select[name='...'] for dropdowns)",
    "selector_type": "css",
    "value": "string value OR array for multiselect OR boolean for checkbox",
    "field_name": "Human readable field name",
    "confidence": 0.0-1.0
}}

IMPORTANT RULES:
1. For <select> elements → ALWAYS use "select_option" action
2. For required fields (*) → MUST provide a value
3. Use user profile data for personal info (state, country, phone, etc.)
4. NEVER skip dropdown/select fields - they are usually required!

REMEMBER: Generate actual values, not placeholders!
"""
    
    def _get_workday_form_system_prompt(self) -> str:
        """System prompt for Workday form analysis."""
        return """You are an AI that fills Workday job application forms.

=== CRITICAL: UNDERSTAND FIELD TYPES ===

There are TWO main types of dropdowns in Workday:

1. **STANDARD HTML <select> ELEMENTS** (MOST COMMON):
   - These show tag='select' and have visible options like ['Select One', 'Alabama', 'Alaska'...]
   - Action: "select_option"
   - Value: EXACT text of option to select (e.g., "California", "United States of America")
   - Use user profile data for State, Country, etc.
   - THESE ARE OFTEN REQUIRED (*) - DO NOT SKIP THEM!

2. **WORKDAY SEARCH-AND-SELECT COMPONENTS** (custom dropdowns):
   - These have NO visible options in HTML (options loaded via API when user types)
   - Used for: "How did you hear about us?", searchable State/Country, etc.
   - Action: "workday_searchable_select" (single value) or "workday_multiselect" (multiple values)
   - Value: Search term(s) to find matching options

=== WORKDAY SEARCH-AND-SELECT BEHAVIOR ===

IMPORTANT: Workday search-and-select components work like this:
1. User types a search term (e.g., "LinkedIn")
2. User presses ENTER to trigger the search
3. Workday fetches matching options via API and displays them
4. User presses ENTER again to select the first/best match

For these fields:
- "How did you hear about us?" → Action: "workday_multiselect", Value: ["LinkedIn"]
- Searchable Country/State → Action: "workday_searchable_select", Value: "United States of America"

=== WORKDAY-SPECIFIC RULES ===

1. SELECTORS: Use these in priority order:
   - data-automation-id: [data-automation-id='addressSection_countryRegion']
   - name attribute: select[name='state']
   - id attribute: #stateSelect

2. STANDARD <select> DROPDOWNS (with visible options):
   - Action: "select_option"
   - Value: EXACT option text from the options list
   - For "State" → Use profile state (e.g., "California", "New York")
   - For "Country" → Use profile country (e.g., "United States of America")
   - MUST fill if marked required (*)

3. SEARCH-AND-SELECT / MULTI-SELECT COMPONENTS:
   - Look for tag='workday_dropdown' or fields like "How did you hear about us?"
   - Action: "workday_multiselect" for multiple values, "workday_searchable_select" for single value
   - Value: Array ["LinkedIn"] or single string "LinkedIn"
   - Common values for "How did you hear about us?": ["LinkedIn"], ["Company Website"], ["Job Board"]

4. CHECKBOXES:
   - Action: "workday_checkbox"
   - Value: true or false

5. RADIO BUTTONS:
   - Action: "workday_radio"
   - Value: Text of option to select (e.g., "Yes", "No")

6. TEXT INPUTS:
   - Action: "type_text"
   - Use user profile data

7. DATE FIELDS:
   - Action: "type_text" with format MM/DD/YYYY

8. FILE UPLOADS:
   - Action: "upload_file"
   - Use resume_path from profile

=== USING PROFILE DATA ===

For personal info fields, ALWAYS use the user profile:
- State field → profile.state (use full name like "California", not abbreviation)
- Country field → profile.country (use "United States of America" not "US")
- Phone → profile.phone
- Email → profile.email
- Name → profile.first_name, profile.last_name

=== OUTPUT REQUIREMENTS ===

1. EVERY <select> element MUST have a "select_option" action
2. EVERY required field (*) MUST have a mapping
3. Use exact option text from the options list when available
4. For search-and-select fields without visible options, provide reasonable search terms
5. For "How did you hear about us?" type fields, use ["LinkedIn"] or similar

Return ONLY valid JSON. No markdown, no explanations."""
    
    def _format_profile_for_prompt(self) -> str:
        """Format user profile for AI prompt."""
        p = self.profile_data
        lines = [
            f"Name: {p.get('first_name', '')} {p.get('middle_name', '')} {p.get('last_name', '')}",
            f"Email: {p.get('email', '')}",
            f"Phone: {p.get('phone', '')}",
            f"Address: {p.get('address_1', '')} {p.get('address_2', '')}",
            f"City: {p.get('city', '')}",
            f"State: {p.get('state', '')}",
            f"ZIP: {p.get('zip_code', '')}",
            f"Country: {p.get('country', '')}",
            f"LinkedIn: {p.get('linkedin_url', '')}",
        ]
        
        # Work experience
        work_exp = p.get('work_experience', [])
        if work_exp:
            lines.append("\nWork Experience:")
            for exp in work_exp[:3]:
                title = exp.get('job_title', exp.get('title', ''))
                company = exp.get('company_name', exp.get('company', ''))
                lines.append(f"  - {title} at {company}")
        
        # Education
        education = p.get('education', [])
        if education:
            lines.append("\nEducation:")
            for edu in education[:2]:
                degree = edu.get('degree', '')
                school = edu.get('university_name', edu.get('school', ''))
                lines.append(f"  - {degree} from {school}")
        
        # Skills
        skills = p.get('skills', [])
        if skills:
            lines.append(f"\nSkills: {', '.join(skills[:10])}")
        
        # File paths
        if p.get('resume_path'):
            lines.append(f"\nResume Path: {p.get('resume_path')}")
        
        return "\n".join(lines)
    
    def _format_inputs_for_prompt(self, inputs: List[Dict]) -> str:
        """Format inputs for AI prompt."""
        lines = []
        select_count = 0
        dropdown_count = 0
        
        for i, inp in enumerate(inputs[:50]):
            tag = inp.get('tag', 'input')
            inp_type = inp.get('type', 'text')
            
            # Mark select/dropdown elements prominently
            if tag == 'select':
                select_count += 1
                parts = [f"{i+1}. [HTML SELECT - USE select_option ACTION]"]
            elif tag == 'workday_dropdown' or inp_type == 'workday_dropdown':
                dropdown_count += 1
                parts = [f"{i+1}. [WORKDAY DROPDOWN - USE workday_searchable_select ACTION]"]
            elif inp_type == 'radiogroup' or tag == 'radiogroup':
                parts = [f"{i+1}. [RADIO GROUP - USE workday_radio ACTION]"]
            elif inp_type == 'checkbox':
                parts = [f"{i+1}. [CHECKBOX - USE workday_checkbox ACTION]"]
            else:
                parts = [f"{i+1}. <{tag}>"]
            
            parts.append(f"type='{inp_type}'")
            
            if inp.get('data-automation-id'):
                parts.append(f"data-automation-id='{inp['data-automation-id']}'")
            if inp.get('id'):
                parts.append(f"id='{inp['id']}'")
            if inp.get('name'):
                parts.append(f"name='{inp['name']}'")
            if inp.get('label'):
                parts.append(f"label='{inp['label'][:50]}'")
            if inp.get('required'):
                parts.append("[REQUIRED *]")
            if inp.get('currentValue'):
                parts.append(f"currentValue='{inp['currentValue'][:30]}'")
            if inp.get('options'):
                # Handle both dict options (from select) and string options (from radiogroup)
                opts = []
                for o in inp['options'][:8]:  # Show more options
                    if isinstance(o, dict):
                        opts.append(str(o.get('text', o.get('value', '')))[:25])
                    else:
                        opts.append(str(o)[:25])
                if len(inp['options']) > 8:
                    opts.append('...')
                parts.append(f"options={opts}")
            
            lines.append(" ".join(parts))
        
        # Add summary for dropdown/select elements
        summary_parts = []
        if select_count > 0:
            summary_parts.append(f"{select_count} HTML SELECT(s) - use select_option")
        if dropdown_count > 0:
            summary_parts.append(f"{dropdown_count} WORKDAY DROPDOWN(s) - use workday_searchable_select")
        
        if summary_parts:
            lines.insert(0, f"*** FOUND: {', '.join(summary_parts)} ***\n")
        
        return "\n".join(lines) if lines else "(No inputs found)"
    
    def _format_buttons_for_prompt(self, buttons: List[Dict]) -> str:
        """Format buttons for AI prompt."""
        lines = []
        for btn in buttons[:20]:
            parts = [f"BUTTON"]
            parts.append(f"text='{btn.get('text', '')[:40]}'")
            if btn.get('data-automation-id'):
                parts.append(f"data-automation-id='{btn['data-automation-id']}'")
            lines.append(" ".join(parts))
        
        return "\n".join(lines) if lines else "(No buttons found)"
    
    def _parse_form_analysis_response(self, content: str):
        """Parse AI response for form analysis."""
        try:
            content = content.strip()
            if content.startswith("```"):
                content = re.sub(r'^```(?:json)?\s*', '', content)
                content = re.sub(r'\s*```$', '', content)
            
            data = json.loads(content)
            
            # Create a response object compatible with existing code
            from dataclasses import dataclass as dc
            
            @dc
            class FormFieldMapping:
                selector: str
                selector_type: str
                action: str
                value: Any
                field_name: str
                confidence: float = 1.0
                select_by: str = "text"
                checked: bool = True
                file_path: Optional[str] = None
                
                def to_autofill_command(self) -> Dict[str, Any]:
                    cmd = {
                        "action": self.action,
                        "selector": self.selector,
                        "selector_type": self.selector_type,
                    }
                    if self.action == "upload_file":
                        cmd["file_path"] = self.file_path
                    elif self.action in ["type_text", "type_number", "enter_date"]:
                        cmd["value"] = self.value
                    elif self.action == "select_option":
                        cmd["value"] = self.value
                        cmd["select_by"] = self.select_by
                    elif self.action == "check":
                        cmd["checked"] = self.checked
                    elif self.action in ["workday_multiselect", "workday_searchable_select"]:
                        cmd["value"] = self.value
                    return cmd
            
            @dc
            class FormAnalysisResponse:
                field_mappings: List = None
                unmapped_fields: List[str] = None
                has_multiselect: bool = False
                
                def __post_init__(self):
                    self.field_mappings = self.field_mappings or []
                    self.unmapped_fields = self.unmapped_fields or []
            
            field_mappings = []
            for mapping in data.get("field_mappings", []):
                field_mappings.append(FormFieldMapping(
                    selector=mapping.get("selector", ""),
                    selector_type=mapping.get("selector_type", "css"),
                    action=mapping.get("action", "type_text"),
                    value=mapping.get("value"),
                    field_name=mapping.get("field_name", ""),
                    confidence=mapping.get("confidence", 1.0),
                    file_path=mapping.get("file_path"),
                ))
            
            return FormAnalysisResponse(
                field_mappings=field_mappings,
                unmapped_fields=data.get("unmapped_fields", []),
                has_multiselect=data.get("has_multiselect", False),
            )
            
        except Exception as e:
            self._log(f"Failed to parse form analysis: {e}", "error")
            return None
    
    # =========================================================================
    # Autofill Execution (with Workday-specific handling)
    # =========================================================================
    
    def _execute_workday_autofill(
        self,
        page,
        field_mappings: List,
    ) -> Tuple[List[FillResult], int, int]:
        """
        Execute autofill commands with Workday-specific handling.
        
        WORKDAY-SPECIFIC ACTIONS:
        - workday_multiselect: Multi-select with Enter after each value
        - workday_searchable_select: Type-to-search dropdown
        - workday_checkbox: Custom checkbox handling
        - workday_radio: Radio button selection
        - type_text: Standard text input
        - select_option: Standard dropdown
        - check: Standard checkbox
        - upload_file: File upload
        """
        if not field_mappings:
            return [], 0, 0
        
        self._log(f"Executing {len(field_mappings)} Workday autofill commands...")
        
        results = []
        filled = 0
        failed = 0
        
        for mapping in field_mappings:
            try:
                action = mapping.action
                selector = mapping.selector
                value = mapping.value
                field_name = getattr(mapping, 'field_name', 'Unknown field')
                
                self._log(f"  Filling: {field_name} ({action})")
                
                # Handle Workday-specific actions
                if action == "workday_multiselect":
                    # Multi-select: Enter each value + press Enter after each
                    result = self._fill_workday_multiselect(page, selector, value, field_name)
                
                elif action == "workday_searchable_select":
                    # Searchable dropdown: Type to search, then select
                    result = self._fill_workday_searchable_select(page, selector, value, field_name)
                
                elif action in ["workday_checkbox", "check"]:
                    # Checkbox: Handle Workday custom checkboxes
                    checked = value if isinstance(value, bool) else str(value).lower() in ('true', 'yes', '1')
                    result = self._fill_workday_checkbox(page, selector, checked, field_name)
                
                elif action in ["workday_radio", "select_radio"]:
                    # Radio button: Select the matching option
                    result = self._fill_workday_radio(page, selector, value, field_name)
                
                elif action == "type_text":
                    # Standard text input - but use Workday's typing method
                    result = self._fill_workday_text_input(page, selector, value, field_name)
                
                elif action == "select_option":
                    # Standard dropdown - try standard select first, then searchable
                    result = self._fill_workday_dropdown(page, selector, value, field_name)
                
                elif action == "workday_dropdown":
                    # Explicit Workday dropdown action
                    result = self._fill_workday_dropdown(page, selector, value, field_name)
                
                elif action == "upload_file":
                    # Use standard autofill engine for file upload
                    cmd = mapping.to_autofill_command()
                    result = self.autofill_engine.execute(cmd)
                
                else:
                    # Fallback to standard autofill engine
                    cmd = mapping.to_autofill_command()
                    result = self.autofill_engine.execute(cmd)
                
                results.append(result)
                
                if result.success:
                    filled += 1
                    self._log(f"    Success: {result.value_used[:50] if result.value_used else 'OK'}")
                else:
                    failed += 1
                    self._log(f"    Failed: {result.error}", "warning")
                
                # Small delay between fields for stability
                time.sleep(0.2)
                    
            except Exception as e:
                self._log(f"    Error: {e}", "error")
                traceback.print_exc()
                failed += 1
        
        self._log(f"Autofill complete: {filled} filled, {failed} failed")
        return results, filled, failed
    
    def _fill_workday_text_input(
        self,
        page,
        selector: str,
        value: str,
        field_name: str
    ) -> FillResult:
        """
        Fill a standard Workday text input.
        Uses type() instead of fill() for better compatibility.
        """
        from autofill.models import FillResult, ActionType
        import time
        
        start_time = time.time()
        
        try:
            self._log(f"    Text input: {field_name}")
            
            # Find the input element
            input_el = page.locator(selector).first
            if not input_el.is_visible():
                return FillResult(
                    success=False,
                    action=ActionType.TYPE_TEXT,
                    selector=selector,
                    error=f"Input not visible: {selector}",
                    duration_ms=int((time.time() - start_time) * 1000),
                )
            
            # Click to focus
            input_el.click()
            time.sleep(0.2)
            
            # Clear existing value
            input_el.fill("")
            time.sleep(0.1)
            
            # Type the value
            input_el.type(str(value), delay=30)
            time.sleep(0.2)
            
            return FillResult(
                success=True,
                action=ActionType.TYPE_TEXT,
                selector=selector,
                value_used=str(value),
                duration_ms=int((time.time() - start_time) * 1000),
            )
            
        except Exception as e:
            return FillResult(
                success=False,
                action=ActionType.TYPE_TEXT,
                selector=selector,
                error=str(e),
                duration_ms=int((time.time() - start_time) * 1000),
            )
    
    def _fill_workday_multiselect(
        self,
        page,
        selector: str,
        values: List[str],
        field_name: str
    ) -> FillResult:
        """
        Fill a Workday multi-select component (search-and-select with multiple values).
        
        WORKDAY MULTI-SELECT BEHAVIOR (Correct Flow):
        For each value:
        1. Click on input to focus
        2. Type a value (e.g., "LinkedIn")
        3. Press ENTER to trigger the search
        4. Wait for dropdown options to appear (loaded via API)
        5. Press ENTER again to select the first/best matching option
           OR click on the matching option
        6. Value is added as a tag/chip in the input
        7. Repeat for each additional value
        
        Example: "How did you hear about us?" with value ["LinkedIn"]
        - Type "LinkedIn" → Press Enter → Wait for options → Press Enter to select
        """
        from autofill.models import FillResult, ActionType
        import time
        
        start_time = time.time()
        successful_values = []
        
        try:
            if not isinstance(values, list):
                values = [values] if values else []
            
            if not values:
                return FillResult(
                    success=False,
                    action=ActionType.TYPE_TEXT,
                    selector=selector,
                    error="No values provided for multiselect",
                    duration_ms=int((time.time() - start_time) * 1000),
                )
            
            self._log(f"    Multiselect: {field_name} with {len(values)} values")
            
            # Find the input element - try multiple selectors
            input_selectors = [
                selector,
                f"{selector} input",
                f"{selector} input[type='text']",
                f"[data-automation-id='searchBox'] input",
                f"[data-automation-id='multiselectInputContainer'] input",
                f"[data-automation-id='selectInputContainer'] input",
            ]
            
            input_el = None
            used_selector = None
            for sel in input_selectors:
                try:
                    el = page.locator(sel).first
                    if el.is_visible():
                        input_el = el
                        used_selector = sel
                        self._log(f"    Found input with: {sel[:50]}")
                        break
                except Exception:
                    continue
            
            if not input_el:
                return FillResult(
                    success=False,
                    action=ActionType.TYPE_TEXT,
                    selector=selector,
                    error=f"Multiselect input not found: {selector}",
                    duration_ms=int((time.time() - start_time) * 1000),
                )
            
            # Process each value one by one using the correct Workday flow
            # IMPORTANT: Use Enter to select, not clicking!
            for i, val in enumerate(values):
                if not val or not str(val).strip():
                    continue
                
                val = str(val).strip()
                self._log(f"    Entering value {i+1}/{len(values)}: '{val}'")
                
                # Step 1: Click to focus the input
                input_el.click()
                time.sleep(0.3)
                
                # Step 2: Clear any existing text
                try:
                    input_el.fill("")
                    time.sleep(0.1)
                except Exception:
                    try:
                        input_el.press("Control+a")
                        input_el.press("Backspace")
                        time.sleep(0.1)
                    except Exception:
                        pass
                
                # Step 3: Type the search value
                input_el.type(val, delay=30)
                self._log(f"    Typed: '{val}'")
                time.sleep(0.3)
                
                # Step 4: Press ENTER to trigger the search
                page.keyboard.press("Enter")
                self._log(f"    Pressed Enter to trigger search")
                
                # Step 5: Wait for options to load from API
                time.sleep(1.2)
                
                # Step 6: ALWAYS press Enter again to select the first/best matching option
                # This is the correct Workday workflow - do NOT try to click options
                page.keyboard.press("Enter")
                self._log(f"    Pressed Enter to select option")
                
                time.sleep(0.5)
                successful_values.append(val)
            
            return FillResult(
                success=len(successful_values) > 0,
                action=ActionType.TYPE_TEXT,
                selector=used_selector or selector,
                value_used=", ".join(successful_values),
                duration_ms=int((time.time() - start_time) * 1000),
            )
            
        except Exception as e:
            self._log(f"    Multiselect error: {e}", "error")
            return FillResult(
                success=False,
                action=ActionType.TYPE_TEXT,
                selector=selector,
                error=str(e),
                duration_ms=int((time.time() - start_time) * 1000),
            )
    
    def _fill_workday_dropdown(
        self,
        page,
        selector: str,
        value: str,
        field_name: str
    ) -> FillResult:
        """
        Fill a Workday standard dropdown/select.
        
        WORKDAY DROPDOWN TYPES:
        1. Standard <select> element - use Selenium's Select class
        2. Custom dropdown (div with role="listbox") - click to open, then select option
        3. Searchable dropdown - falls back to searchable select method
        """
        from autofill.models import FillResult, ActionType
        import time
        
        start_time = time.time()
        value_str = str(value).strip()
        
        try:
            self._log(f"    Dropdown: {field_name} = '{value_str}'")
            
            # Try to find the element
            element = None
            element_type = None
            
            # Pattern 1: Standard <select> element
            select_selectors = [
                selector,
                f"{selector} select",
                f"select[data-automation-id*='{field_name.lower().replace(' ', '')}']",
                f"select[name*='{field_name.lower().replace(' ', '')}']",
                f"label:has-text('{field_name}') ~ select",
                f"label:has-text('{field_name}') + select",
            ]
            
            for sel in select_selectors:
                try:
                    el = page.locator(sel).first
                    if el.is_visible():
                        # Check if it's a real <select> element
                        tag = el.get_attribute("tagName") or ""
                        if tag.lower() == "select" or "select" in sel:
                            element = el
                            element_type = "select"
                            self._log(f"    Found <select> with: {sel[:50]}")
                            break
                except Exception:
                    continue
            
            # Pattern 2: Workday custom dropdown button (click to open listbox)
            if not element:
                dropdown_selectors = [
                    selector,
                    f"{selector} button",
                    f"[data-automation-id*='dropdown']",
                    f"[data-automation-id*='select']",
                    f"button[aria-haspopup='listbox']",
                    f"div[role='combobox']",
                    f"div:has-text('{field_name}') button",
                ]
                
                for sel in dropdown_selectors:
                    try:
                        el = page.locator(sel).first
                        if el.is_visible():
                            element = el
                            element_type = "custom"
                            self._log(f"    Found custom dropdown with: {sel[:50]}")
                            break
                    except Exception:
                        continue
            
            if not element:
                # Fall back to searchable select
                self._log(f"    No standard dropdown found, trying searchable select...")
                return self._fill_workday_searchable_select(page, selector, value_str, field_name)
            
            # Handle based on element type
            if element_type == "select":
                # Use Selenium's select_by_visible_text or select_by_value
                try:
                    from selenium.webdriver.support.ui import Select
                    
                    # Get the underlying Selenium element
                    elements = element._find_elements()
                    if elements:
                        select = Select(elements[0])
                        
                        # Try to select by visible text first
                        try:
                            select.select_by_visible_text(value_str)
                            time.sleep(0.3)
                            self._log(f"    Selected by text: {value_str}")
                            return FillResult(
                                success=True,
                                action=ActionType.SELECT_OPTION,
                                selector=selector,
                                value_used=value_str,
                                duration_ms=int((time.time() - start_time) * 1000),
                            )
                        except Exception:
                            pass
                        
                        # Try partial text match
                        for option in select.options:
                            if value_str.lower() in option.text.lower():
                                select.select_by_visible_text(option.text)
                                time.sleep(0.3)
                                self._log(f"    Selected partial match: {option.text}")
                                return FillResult(
                                    success=True,
                                    action=ActionType.SELECT_OPTION,
                                    selector=selector,
                                    value_used=option.text,
                                    duration_ms=int((time.time() - start_time) * 1000),
                                )
                        
                        # Try to select by value
                        try:
                            select.select_by_value(value_str)
                            time.sleep(0.3)
                            self._log(f"    Selected by value: {value_str}")
                            return FillResult(
                                success=True,
                                action=ActionType.SELECT_OPTION,
                                selector=selector,
                                value_used=value_str,
                                duration_ms=int((time.time() - start_time) * 1000),
                            )
                        except Exception:
                            pass
                            
                except Exception as e:
                    self._log(f"    Selenium Select failed: {e}", "warning")
            
            # Custom dropdown: Click to open, then select option
            if element_type == "custom" or not element_type:
                # Click to open dropdown
                element.click()
                time.sleep(0.5)
                
                # Look for the option in the listbox
                option_selectors = [
                    f"[role='option']:has-text('{value_str}')",
                    f"[data-automation-id='promptOption']:has-text('{value_str}')",
                    f"li:has-text('{value_str}')",
                    f"div[role='listbox'] div:has-text('{value_str}')",
                    f"ul li:has-text('{value_str}')",
                    f"option:has-text('{value_str}')",
                ]
                
                for opt_sel in option_selectors:
                    try:
                        option = page.locator(opt_sel).first
                        if option.is_visible(timeout=1000):
                            option.click()
                            time.sleep(0.3)
                            self._log(f"    Clicked dropdown option: {value_str}")
                            return FillResult(
                                success=True,
                                action=ActionType.SELECT_OPTION,
                                selector=opt_sel,
                                value_used=value_str,
                                duration_ms=int((time.time() - start_time) * 1000),
                            )
                    except Exception:
                        continue
                
                # Try partial text match
                partial_selectors = [
                    f"[role='option']",
                    f"li",
                    f"[data-automation-id='promptOption']",
                ]
                
                for ps in partial_selectors:
                    try:
                        options = page.locator(ps)
                        count = options.count()
                        for i in range(min(count, 20)):
                            opt = options.nth(i)
                            if opt.is_visible():
                                text = opt.text_content()
                                if text and value_str.lower() in text.lower():
                                    opt.click()
                                    time.sleep(0.3)
                                    self._log(f"    Clicked partial match: {text[:50]}")
                                    return FillResult(
                                        success=True,
                                        action=ActionType.SELECT_OPTION,
                                        selector=ps,
                                        value_used=text.strip(),
                                        duration_ms=int((time.time() - start_time) * 1000),
                                    )
                    except Exception:
                        continue
                
                # Press Escape to close dropdown if nothing found
                try:
                    page.keyboard.press("Escape")
                except Exception:
                    pass
            
            # Fall back to searchable select as last resort
            self._log(f"    Dropdown selection failed, trying searchable select...")
            return self._fill_workday_searchable_select(page, selector, value_str, field_name)
            
        except Exception as e:
            self._log(f"    Dropdown error: {e}", "error")
            return FillResult(
                success=False,
                action=ActionType.SELECT_OPTION,
                selector=selector,
                error=str(e),
                duration_ms=int((time.time() - start_time) * 1000),
            )
    
    def _fill_workday_searchable_select(
        self,
        page,
        selector: str,
        value: str,
        field_name: str
    ) -> FillResult:
        """
        Fill a Workday searchable dropdown (search-and-select component).
        
        WORKDAY SEARCHABLE SELECT BEHAVIOR:
        This is the correct flow based on how Workday search-and-select works:
        
        1. Click on the input to focus it
        2. Type the search value (e.g., "LinkedIn")
        3. Press ENTER to trigger the search
        4. Wait for the platform to fetch and display matching options from API
        5. Press ENTER again to select the first/best matching option
        
        Example: "How did you hear about us?" with value "LinkedIn"
        - Type "LinkedIn" → Press Enter → Wait → Press Enter to select
        
        IMPORTANT: Always use Enter to select, not clicking!
        """
        from autofill.models import FillResult, ActionType
        import time
        
        start_time = time.time()
        value_str = str(value).strip()
        
        try:
            self._log(f"    Searchable select: {field_name} = '{value_str}'")
            
            # Find the input element - try multiple selectors
            input_selectors = [
                selector,
                f"{selector} input",
                f"{selector} input[type='text']",
                f"[data-automation-id='searchBox'] input",
                f"[data-automation-id='selectInputContainer'] input",
                f"[data-automation-id='multiselectInputContainer'] input",
            ]
            
            input_el = None
            used_selector = None
            for sel in input_selectors:
                try:
                    el = page.locator(sel).first
                    if el.is_visible():
                        input_el = el
                        used_selector = sel
                        self._log(f"    Found input with: {sel[:50]}")
                        break
                except Exception:
                    continue
            
            if not input_el:
                return FillResult(
                    success=False,
                    action=ActionType.SELECT_OPTION,
                    selector=selector,
                    error=f"Searchable select input not found: {selector}",
                    duration_ms=int((time.time() - start_time) * 1000),
                )
            
            # Step 1: Click to focus the input
            input_el.click()
            time.sleep(0.3)
            
            # Step 2: Clear any existing value
            try:
                input_el.fill("")
                time.sleep(0.1)
            except Exception:
                # Try select all + delete as fallback
                try:
                    input_el.press("Control+a")
                    input_el.press("Backspace")
                    time.sleep(0.1)
                except Exception:
                    pass
            
            # Step 3: Type the search value
            input_el.type(value_str, delay=30)
            self._log(f"    Typed: '{value_str}'")
            time.sleep(0.3)
            
            # Step 4: Press ENTER to trigger the search
            page.keyboard.press("Enter")
            self._log(f"    Pressed Enter to trigger search")
            
            # Step 5: Wait for options to load from API
            time.sleep(1.2)
            
            # Step 6: ALWAYS press Enter again to select the first/best matching option
            # This is the correct Workday workflow - do NOT try to click options
            page.keyboard.press("Enter")
            self._log(f"    Pressed Enter to select option")
            
            time.sleep(0.5)
            
            return FillResult(
                success=True,
                action=ActionType.SELECT_OPTION,
                selector=used_selector or selector,
                value_used=value_str,
                duration_ms=int((time.time() - start_time) * 1000),
            )
            
        except Exception as e:
            self._log(f"    Searchable select error: {e}", "error")
            return FillResult(
                success=False,
                action=ActionType.SELECT_OPTION,
                selector=selector,
                error=str(e),
                duration_ms=int((time.time() - start_time) * 1000),
            )
    
    def _fill_workday_checkbox(
        self,
        page,
        selector: str,
        checked: bool,
        field_name: str
    ) -> FillResult:
        """
        Handle Workday checkbox components.
        
        WORKDAY CHECKBOX BEHAVIOR:
        - Workday uses custom checkbox components (divs with role="checkbox")
        - Also uses standard input[type="checkbox"] in some cases
        - May use data-automation-id attributes
        """
        from autofill.models import FillResult, ActionType
        import time
        
        start_time = time.time()
        
        try:
            self._log(f"    Checkbox: {field_name} = {checked}")
            
            # Build list of selectors to try (Workday-specific patterns)
            checkbox_selectors = [
                # Direct selector
                selector,
                # Workday custom checkbox patterns
                f"[role='checkbox'][aria-label*='{field_name}']",
                f"[data-automation-id*='checkbox']",
                # Standard checkbox within selector
                f"{selector} input[type='checkbox']",
                # Checkbox by label text
                f"//label[contains(text(), '{field_name}')]//input[@type='checkbox']",
                f"//input[@type='checkbox']/following-sibling::*[contains(text(), '{field_name}')]",
                # Workday label pattern
                f"label:has-text('{field_name}') input[type='checkbox']",
                f"div:has-text('{field_name}') input[type='checkbox']",
            ]
            
            checkbox_el = None
            used_selector = None
            
            for sel in checkbox_selectors:
                try:
                    el = page.locator(sel).first
                    if el.is_visible():
                        checkbox_el = el
                        used_selector = sel
                        self._log(f"    Found checkbox with: {sel[:50]}")
                        break
                except Exception:
                    continue
            
            if not checkbox_el:
                # Try finding by looking for the text and nearby checkbox
                try:
                    # Find parent containing the field name, then find checkbox inside
                    parent = page.locator(f"div:has-text('{field_name}')").first
                    if parent.is_visible():
                        checkbox_el = parent.locator("input[type='checkbox']").first
                        if checkbox_el.is_visible():
                            used_selector = "nested checkbox"
                            self._log(f"    Found nested checkbox")
                except Exception:
                    pass
            
            if not checkbox_el:
                return FillResult(
                    success=False,
                    action=ActionType.CHECK,
                    selector=selector,
                    error=f"Checkbox not found: {field_name}",
                    duration_ms=int((time.time() - start_time) * 1000),
                )
            
            # Get current state
            try:
                is_checked = checkbox_el.is_checked()
            except Exception:
                # For custom checkboxes, check aria-checked attribute
                try:
                    aria_checked = checkbox_el.get_attribute("aria-checked")
                    is_checked = aria_checked == "true"
                except Exception:
                    is_checked = False
            
            # Click only if state needs to change
            if is_checked != checked:
                try:
                    checkbox_el.click()
                    time.sleep(0.3)
                    self._log(f"    Checkbox toggled to: {checked}")
                except Exception:
                    # Try clicking parent label as fallback
                    try:
                        label = page.locator(f"label:has-text('{field_name}')").first
                        if label.is_visible():
                            label.click()
                            time.sleep(0.3)
                            self._log(f"    Clicked label to toggle checkbox")
                    except Exception as e:
                        self._log(f"    Checkbox click failed: {e}", "warning")
            else:
                self._log(f"    Checkbox already in desired state: {checked}")
            
            return FillResult(
                success=True,
                action=ActionType.CHECK,
                selector=selector,
                value_used=str(checked),
                duration_ms=int((time.time() - start_time) * 1000),
            )
            
        except Exception as e:
            self._log(f"    Checkbox error: {e}", "error")
            return FillResult(
                success=False,
                action=ActionType.CHECK,
                selector=selector,
                error=str(e),
                duration_ms=int((time.time() - start_time) * 1000),
            )
    
    def _fill_workday_radio(
        self,
        page,
        selector: str,
        value: str,
        field_name: str
    ) -> FillResult:
        """
        Handle Workday radio button components.
        
        WORKDAY RADIO BEHAVIOR:
        - Workday uses custom radio components (divs with role="radio")
        - Often organized in radiogroups with role="radiogroup"
        - May use data-automation-id attributes
        - Options like "Yes", "No" are clickable divs/labels
        """
        from autofill.models import FillResult, ActionType
        import time
        
        start_time = time.time()
        value_str = str(value).strip()
        
        try:
            self._log(f"    Radio: {field_name} = '{value_str}'")
            
            # Normalize common values
            value_lower = value_str.lower()
            if value_lower in ('true', 'yes', '1'):
                value_variations = ['Yes', 'yes', 'YES', 'True', 'true']
            elif value_lower in ('false', 'no', '0'):
                value_variations = ['No', 'no', 'NO', 'False', 'false']
            else:
                value_variations = [value_str, value_str.capitalize(), value_str.lower(), value_str.upper()]
            
            # Try multiple selector patterns for Workday radio buttons
            for val in value_variations:
                radio_selectors = [
                    # Workday custom radio with role="radio"
                    f"[role='radio'][aria-label='{val}']",
                    f"[role='radio']:has-text('{val}')",
                    # Workday data-automation-id patterns
                    f"[data-automation-id*='radio']:has-text('{val}')",
                    f"[data-automation-id*='Radio']:has-text('{val}')",
                    # Label patterns for Yes/No questions
                    f"label:has-text('{val}')",
                    f"div[role='radio']:has-text('{val}')",
                    # Standard radio input patterns
                    f"input[type='radio'][value='{val}']",
                    f"input[type='radio'][value='{val.lower()}']",
                    f"label:has-text('{val}') input[type='radio']",
                    # XPath for text content matching
                    f"//label[normalize-space()='{val}']",
                    f"//div[@role='radio'][contains(text(), '{val}')]",
                    f"//span[normalize-space()='{val}']/ancestor::label",
                    # Workday specific label+radio pattern
                    f"//label[.//text()[normalize-space()='{val}']]",
                ]
                
                for sel in radio_selectors:
                    try:
                        radio_el = page.locator(sel).first
                        if radio_el.is_visible():
                            radio_el.click()
                            time.sleep(0.3)
                            self._log(f"    Selected radio option '{val}' with: {sel[:40]}")
                            return FillResult(
                                success=True,
                                action=ActionType.SELECT_RADIO,
                                selector=sel,
                                value_used=val,
                                duration_ms=int((time.time() - start_time) * 1000),
                            )
                    except Exception:
                        continue
            
            # Fallback: Try to find the field by question text, then click the matching option
            try:
                self._log(f"    Trying fallback: find question '{field_name}', click '{value_str}'")
                
                # Find the question/label container
                question_container = None
                question_patterns = [
                    f"div:has-text('{field_name[:30]}')",
                    f"legend:has-text('{field_name[:30]}')",
                    f"[data-automation-id*='question']:has-text('{field_name[:30]}')",
                ]
                
                for qp in question_patterns:
                    try:
                        container = page.locator(qp).first
                        if container.is_visible():
                            question_container = container
                            break
                    except Exception:
                        continue
                
                if question_container:
                    # Now find the radio option within this container
                    for val in value_variations:
                        option_patterns = [
                            f"label:has-text('{val}')",
                            f"[role='radio']:has-text('{val}')",
                            f"span:has-text('{val}')",
                        ]
                        for op in option_patterns:
                            try:
                                option = question_container.locator(op).first
                                if option.is_visible():
                                    option.click()
                                    time.sleep(0.3)
                                    self._log(f"    Fallback: clicked '{val}' in question container")
                                    return FillResult(
                                        success=True,
                                        action=ActionType.SELECT_RADIO,
                                        selector=f"fallback:{field_name}",
                                        value_used=val,
                                        duration_ms=int((time.time() - start_time) * 1000),
                                    )
                            except Exception:
                                continue
            except Exception as e:
                self._log(f"    Fallback failed: {e}", "warning")
            
            return FillResult(
                success=False,
                action=ActionType.SELECT_RADIO,
                selector=selector,
                error=f"Radio option not found: {field_name} = {value_str}",
                duration_ms=int((time.time() - start_time) * 1000),
            )
            
        except Exception as e:
            self._log(f"    Radio error: {e}", "error")
            return FillResult(
                success=False,
                action=ActionType.SELECT_RADIO,
                selector=selector,
                error=str(e),
                duration_ms=int((time.time() - start_time) * 1000),
            )
    
    # =========================================================================
    # Helper Methods
    # =========================================================================
    
    def _extract_page_content(self, page) -> PageContent:
        """Extract and filter page content for AI analysis."""
        return self.page_analyzer.analyze(page)
    
    def _check_for_captcha(self, page) -> CaptchaDetectionResult:
        """Check if CAPTCHA is present."""
        if self.captcha_detector:
            return self.captcha_detector.detect_from_page(page)
        
        from automation.captcha_detector import CaptchaDetectionResult
        return CaptchaDetectionResult(detected=False)
    
    def _handle_captcha_pause(
        self,
        page,
        captcha_result: CaptchaDetectionResult,
        total_filled: int,
        total_failed: int,
        page_num: int,
        all_unmapped: List[str],
    ) -> WorkflowResult:
        """Handle CAPTCHA by pausing workflow."""
        self._log(f"CAPTCHA detected: {captcha_result.captcha_type}")
        
        if self.notifier:
            self.notifier.notify_captcha_detected(
                job_id=self.job_id,
                profile_id=self.profile_data.get("id"),
                captcha_type=captcha_result.captcha_type,
                url=page.url,
            )
        
        if self.storage:
            self.storage.set_session_status(
                self.job_id,
                "captcha_waiting",
                f"CAPTCHA detected ({captcha_result.captcha_type}). Please solve to continue.",
            )
        
        return WorkflowResult(
            success=True,
            page_number=page_num,
            fields_filled=total_filled,
            fields_failed=total_failed,
            captcha_detected=True,
            captcha_type=captcha_result.captcha_type,
            paused=True,
            pause_reason=f"CAPTCHA detected: {captcha_result.captcha_type}",
            unmapped_fields=all_unmapped,
            platform=self.PLATFORM_NAME,
        )
    
    def _wait_for_page_load(self, page) -> None:
        """Wait for Workday page to fully load."""
        try:
            page.wait_for_load_state("networkidle", timeout=15000)
        except Exception:
            pass
        time.sleep(1)  # Additional wait for Workday's dynamic content
    
    def _save_autofill_results(self, results: List[FillResult], ai_response) -> None:
        """Save autofill results to session storage."""
        if not self.storage:
            return
        
        result_dicts = []
        for i, result in enumerate(results):
            field_name = ""
            if ai_response and i < len(ai_response.field_mappings):
                field_name = ai_response.field_mappings[i].field_name
            
            action_str = result.action.value if hasattr(result.action, 'value') else str(result.action)
            
            result_dicts.append({
                "field_name": field_name,
                "selector": result.selector,
                "action": action_str,
                "value": result.value_used,
                "success": result.success,
                "error": result.error,
                "duration_ms": result.duration_ms,
            })
        
        self.storage.add_autofill_results(self.job_id, result_dicts)
    
    def pre_process_hook(self, page) -> None:
        """Workday-specific pre-processing."""
        # Close any cookie banners or popups
        popup_selectors = [
            "[data-automation-id='closeModal']",
            "button:has-text('Accept')",
            "button:has-text('Close')",
            "[aria-label='Close']",
        ]
        
        for selector in popup_selectors:
            try:
                el = page.locator(selector).first
                if el.is_visible(timeout=1000):
                    el.click()
                    self._log("Closed popup/modal")
                    time.sleep(0.5)
            except Exception:
                continue
    
    def post_process_hook(self, page, result: WorkflowResult) -> WorkflowResult:
        """Workday-specific post-processing."""
        result.platform = self.PLATFORM_NAME
        return result

