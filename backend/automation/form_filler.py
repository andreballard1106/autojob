import logging
import sys
import traceback
from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Tuple

from autofill import AutofillEngine
from autofill.models import FillResult
from automation.ai_service import AIService
from automation.session_storage import SessionStorage, session_storage
from automation.page_analyzer import PageAnalyzer, PageContent
from automation.captcha_detector import CaptchaDetector, CaptchaDetectionResult, captcha_detector
from automation.notification_service import NotificationService, notification_service
from automation.application_logger import ApplicationLogger, LogAction, application_logger

logger = logging.getLogger(__name__)


def _log_error(message: str, exc: Exception = None):
    """Log error to console with traceback."""
    print(f"[ERROR] {message}", flush=True)
    if exc:
        print(f"[ERROR] Exception: {exc}", flush=True)
        traceback.print_exc()
    sys.stdout.flush()


MAX_NAVIGATION_ATTEMPTS = 5
MAX_FORM_PAGES = 10


@dataclass
class FormFillingResult:
    success: bool
    page_number: int
    fields_filled: int
    fields_failed: int
    needs_more_navigation: bool
    submit_ready: bool
    error: Optional[str] = None
    unmapped_fields: List[str] = None
    captcha_detected: bool = False
    captcha_type: Optional[str] = None
    paused: bool = False
    pause_reason: Optional[str] = None
    
    def __post_init__(self):
        self.unmapped_fields = self.unmapped_fields or []


class FormFiller:
    def __init__(
        self,
        driver,
        ai_service: AIService,
        profile_data: Dict[str, Any],
        job_id: str,
        storage: SessionStorage = None,
        detector: CaptchaDetector = None,
        notifier: NotificationService = None,
        app_logger: ApplicationLogger = None,
    ):
        self.driver = driver
        self.ai_service = ai_service
        self.profile_data = profile_data
        self.job_id = job_id
        self.storage = storage or session_storage
        self.captcha_detector = detector or captcha_detector
        self.notifier = notifier or notification_service
        self.app_logger = app_logger or application_logger
        
        self.autofill_engine = AutofillEngine(driver)
        self.page_analyzer = PageAnalyzer()
        
        self._last_ai_response = None
        
        self.autofill_engine.configure(
            stop_on_error=False,
            retry_count=2,
            retry_delay_ms=500,
        )
    
    def _extract_page_content(self, page) -> PageContent:
        """Extract and filter page content for AI analysis."""
        print(f"  [EXTRACT] Analyzing page content...")
        content = self.page_analyzer.analyze(page)
        print(f"  [EXTRACT] Found {len(content.inputs)} inputs, {len(content.buttons)} buttons")
        return content
    
    def _check_for_captcha(self, page, page_content: PageContent) -> CaptchaDetectionResult:
        """Check if CAPTCHA is present on page."""
        page_result = self.captcha_detector.detect_from_page(page)
        if page_result.detected:
            return page_result
        return self.captcha_detector.detect_from_html(page_content.filtered_html)
    
    def _execute_autofill_commands(self, ai_response) -> Tuple[List[FillResult], int, int]:
        """Execute autofill commands from AI response."""
        if not ai_response.field_mappings:
            print(f"  [FILL] No field mappings to execute")
            return [], 0, 0
        
        print(f"  [FILL] Executing {len(ai_response.field_mappings)} autofill commands...")
        
        commands = []
        for mapping in ai_response.field_mappings:
            cmd = mapping.to_autofill_command()
            commands.append(cmd)
            print(f"       - {mapping.field_name}: {mapping.action} -> {mapping.selector[:50]}")
        
        results = self.autofill_engine.execute_all(commands)
        
        filled = sum(1 for r in results if r.success)
        failed = sum(1 for r in results if not r.success)
        
        for i, result in enumerate(results):
            if not result.success:
                field_name = ai_response.field_mappings[i].field_name if i < len(ai_response.field_mappings) else "unknown"
                print(f"  [FILL] FAILED: {field_name} - {result.error}")
        
        print(f"  [FILL] Result: {filled} filled, {failed} failed")
        return results, filled, failed
    
    def _save_autofill_results(self, results: List[FillResult], ai_response) -> None:
        """Save autofill results to session storage."""
        result_dicts = []
        
        for i, result in enumerate(results):
            field_name = ""
            if i < len(ai_response.field_mappings):
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
            
            self.app_logger.log_sync(
                job_id=self.job_id,
                action=LogAction.FIELD_FILLED if result.success else LogAction.FIELD_FAILED,
                details={
                    "field_name": field_name,
                    "selector": result.selector,
                    "action_type": action_str,
                    "success": result.success,
                    "error": result.error,
                    "duration_ms": result.duration_ms,
                },
            )
        
        self.storage.add_autofill_results(self.job_id, result_dicts)
    
    def _click_navigation_button(self, page, button_info: Dict, button_type: str = "next") -> bool:
        """Click a navigation button (next/submit) using AI-detected selector."""
        if not button_info:
            return False
        
        selector = button_info.get('selector', '')
        selector_type = button_info.get('selector_type', 'css')
        button_text = button_info.get('text', button_type)
        
        if not selector:
            return False
        
        print(f"  [NAV] Clicking {button_type} button: {selector}")
        
        try:
            if selector_type == 'xpath':
                locator = page.locator(f"xpath={selector}")
            else:
                locator = page.locator(selector)
            
            btn = locator.first
            if btn.is_visible():
                btn.click()
                print(f"  [NAV] Clicked '{button_text}' successfully")
                return True
            else:
                print(f"  [NAV] Button not visible: {selector}")
        except Exception as e:
            print(f"  [NAV] Failed to click button: {e}")
        
        return False
    
    def _click_next_button_fallback(self, page) -> bool:
        """Fallback: Try common next button patterns."""
        patterns = [
            "button:has-text('Next')",
            "button:has-text('Continue')",
            "button:has-text('Save and Continue')",
            "button:has-text('Save & Continue')",
            "[data-automation-id='bottom-navigation-next-button']",
            "input[type='submit'][value*='Next']",
            "input[type='submit'][value*='Continue']",
        ]
        
        for pattern in patterns:
            try:
                btn = page.locator(pattern).first
                if btn.is_visible():
                    print(f"  [NAV] Fallback: clicking {pattern}")
                    btn.click()
                    return True
            except Exception:
                continue
        
        return False
    
    def _try_click_apply_button(self, page) -> bool:
        """Try to find and click common Apply/Start buttons on landing pages."""
        apply_patterns = [
            # Common "Apply" button patterns
            "button:has-text('Apply')",
            "button:has-text('Apply Now')",
            "button:has-text('Apply for this job')",
            "button:has-text('Apply for Job')",
            "a:has-text('Apply')",
            "a:has-text('Apply Now')",
            "[data-automation-id='jobPostingApplyButton']",
            "[data-testid='apply-button']",
            "[aria-label*='Apply']",
            "input[type='submit'][value*='Apply']",
            # Common "Start" button patterns
            "button:has-text('Start Application')",
            "button:has-text('Start')",
            "a:has-text('Start Application')",
            "a:has-text('Start')",
            # Other common patterns
            "button:has-text('Begin Application')",
            "button:has-text('Get Started')",
            "button:has-text('Submit Application')",
            "[class*='apply-button']",
            "[class*='applyButton']",
            "[id*='apply']",
        ]
        
        for pattern in apply_patterns:
            try:
                locator = page.locator(pattern)
                if locator.first and locator.first.is_visible():
                    print(f"  [NAV] Found Apply button: {pattern}")
                    locator.first.click()
                    return True
            except Exception:
                continue
        
        # Also try XPath patterns for more complex selectors
        xpath_patterns = [
            "//button[contains(translate(text(), 'APPLY', 'apply'), 'apply')]",
            "//a[contains(translate(text(), 'APPLY', 'apply'), 'apply')]",
            "//button[contains(@class, 'apply')]",
            "//a[contains(@class, 'apply')]",
        ]
        
        for xpath in xpath_patterns:
            try:
                locator = page.locator(f"xpath={xpath}")
                if locator.first and locator.first.is_visible():
                    print(f"  [NAV] Found Apply button via XPath: {xpath[:50]}...")
                    locator.first.click()
                    return True
            except Exception:
                continue
        
        return False
    
    def _handle_captcha_pause(
        self,
        page,
        captcha_result: CaptchaDetectionResult,
        fields_filled: int,
        fields_failed: int,
        page_number: int,
        ai_response,
    ) -> FormFillingResult:
        """Handle CAPTCHA detection - form is filled, now pause for user."""
        print(f"  [CAPTCHA] Detected: {captcha_result.captcha_type}")
        print(f"  [CAPTCHA] Form filled with {fields_filled} fields, pausing for user action")
        
        current_url = ""
        try:
            current_url = page.url
        except Exception:
            pass
        
        self.app_logger.log_sync(
            job_id=self.job_id,
            action=LogAction.CAPTCHA_DETECTED,
            details={
                "captcha_type": captcha_result.captcha_type,
                "confidence": captcha_result.confidence,
                "fields_filled": fields_filled,
                "page_number": page_number,
                "url": current_url,
            },
        )
        
        self.notifier.notify_captcha_detected(
            job_id=self.job_id,
            profile_id=self.profile_data.get("id"),
            captcha_type=captcha_result.captcha_type,
            url=current_url,
        )
        
        self.storage.set_session_status(
            self.job_id,
            "captcha_waiting",
            f"CAPTCHA detected ({captcha_result.captcha_type}). {fields_filled} fields filled. Waiting for user.",
        )
        
        has_next = ai_response.next_button is not None if ai_response else False
        has_submit = ai_response.submit_button is not None if ai_response else False
        
        return FormFillingResult(
            success=True,
            page_number=page_number,
            fields_filled=fields_filled,
            fields_failed=fields_failed,
            needs_more_navigation=has_next,
            submit_ready=has_submit and not has_next,
            captcha_detected=True,
            captcha_type=captcha_result.captcha_type,
            paused=True,
            pause_reason=f"CAPTCHA detected: {captcha_result.captcha_type}. Please solve and click Continue.",
            unmapped_fields=ai_response.unmapped_fields if ai_response else [],
        )
    
    def process_page(self, page) -> FormFillingResult:
        """Process a single page: extract content, call AI, execute autofill."""
        try:
            return self._process_page_internal(page)
        except Exception as e:
            _log_error(f"Error processing page: {e}", e)
            return FormFillingResult(
                success=False,
                page_number=0,
                fields_filled=0,
                fields_failed=0,
                needs_more_navigation=False,
                submit_ready=False,
                error=f"Page processing error: {str(e)}",
            )
    
    def _process_page_internal(self, page) -> FormFillingResult:
        """Internal page processing with error handling at caller."""
        
        page_content = self._extract_page_content(page)
        
        self.storage.add_page_snapshot(self.job_id, page_content.to_dict())
        
        captcha_result = self._check_for_captcha(page, page_content)
        has_captcha = captcha_result.detected
        
        if has_captcha:
            print(f"  [CAPTCHA] Detected on page: {captcha_result.captcha_type}")
        
        print(f"  [AI] Calling OpenAI to analyze page and generate commands...")
        ai_response = self.ai_service.analyze_and_generate_commands_sync(
            page_content.to_dict(),
            self.profile_data,
        )
        self._last_ai_response = ai_response
        
        print(f"  [AI] Response: page_type={ai_response.page_type}, "
              f"is_form={ai_response.is_form_page}, "
              f"confidence={ai_response.confidence:.2f}")
        print(f"  [AI] Commands: {len(ai_response.field_mappings)} fields, "
              f"{len(ai_response.navigation_actions)} nav actions")
        
        if ai_response.next_button:
            print(f"  [AI] Next button: {ai_response.next_button.get('selector', 'N/A')}")
        if ai_response.submit_button:
            print(f"  [AI] Submit button: {ai_response.submit_button.get('selector', 'N/A')}")
        
        if ai_response.needs_navigation and not has_captcha:
            print(f"  [NAV] Page needs navigation first...")
            for nav in ai_response.navigation_actions:
                cmd = nav.to_autofill_command()
                self.autofill_engine.execute(cmd)
            
            return FormFillingResult(
                success=True,
                page_number=0,
                fields_filled=0,
                fields_failed=0,
                needs_more_navigation=True,
                submit_ready=False,
            )
        
        filled = 0
        failed = 0
        results = []
        
        if ai_response.is_form_page and ai_response.field_mappings:
            results, filled, failed = self._execute_autofill_commands(ai_response)
            self._save_autofill_results(results, ai_response)
        
        session = self.storage.get_session(self.job_id)
        page_number = session.current_page if session else 1
        
        has_next = ai_response.next_button is not None
        has_submit = ai_response.submit_button is not None
        
        if has_captcha:
            return self._handle_captcha_pause(
                page=page,
                captcha_result=captcha_result,
                fields_filled=filled,
                fields_failed=failed,
                page_number=page_number,
                ai_response=ai_response,
            )
        
        # If not a form page, try to find and click "Apply" or "Start" buttons
        if not ai_response.is_form_page and not ai_response.field_mappings:
            print(f"  [NAV] Page is not a form, looking for Apply/Start buttons...")
            
            # Try to find common "Apply" or "Start Application" buttons
            if self._try_click_apply_button(page):
                print(f"  [NAV] Clicked apply button, waiting for form to load...")
                try:
                    page.wait_for_load_state("networkidle", timeout=5000)
                except Exception:
                    pass
                
                return FormFillingResult(
                    success=True,
                    page_number=page_number,
                    fields_filled=0,
                    fields_failed=0,
                    needs_more_navigation=True,
                    submit_ready=False,
                )
            
            # If AI detected a next/submit button, use that for navigation
            if has_next or has_submit:
                print(f"  [NAV] Found navigation button, will try to proceed...")
                return FormFillingResult(
                    success=True,
                    page_number=page_number,
                    fields_filled=0,
                    fields_failed=0,
                    needs_more_navigation=True,
                    submit_ready=False,
                )
            
            # No form and no navigation options - this might be a confirmation page or error
            print(f"  [WARN] No form fields or navigation buttons found")
            return FormFillingResult(
                success=False,
                page_number=page_number,
                fields_filled=0,
                fields_failed=0,
                needs_more_navigation=False,
                submit_ready=False,
                error="Not a form page and no navigation buttons found. The page might be a confirmation page or require manual navigation.",
            )
        
        return FormFillingResult(
            success=filled > 0 or failed == 0,
            page_number=page_number,
            fields_filled=filled,
            fields_failed=failed,
            needs_more_navigation=has_next,
            submit_ready=has_submit and not has_next,
            unmapped_fields=ai_response.unmapped_fields,
        )
    
    def process_application(self, page) -> FormFillingResult:
        """Process entire job application (potentially multi-page)."""
        try:
            return self._process_application_internal(page)
        except Exception as e:
            _log_error(f"Error processing application: {e}", e)
            self.storage.set_session_status(self.job_id, "error", str(e))
            self.app_logger.log_sync(
                job_id=self.job_id,
                action=LogAction.ERROR,
                details={"error": str(e), "traceback": traceback.format_exc()},
            )
            return FormFillingResult(
                success=False,
                page_number=0,
                fields_filled=0,
                fields_failed=0,
                needs_more_navigation=False,
                submit_ready=False,
                error=f"Application processing error: {str(e)}",
            )
    
    def _process_application_internal(self, page) -> FormFillingResult:
        """Internal application processing."""
        
        session = self.storage.get_session(self.job_id)
        if not session:
            session = self.storage.create_session(
                job_id=self.job_id,
                profile_id=self.profile_data.get("id", ""),
                url=page.url,
            )
        
        self.app_logger.log_sync(
            job_id=self.job_id,
            action=LogAction.PROCESSING_STARTED,
            details={
                "url": page.url,
                "profile_id": self.profile_data.get("id", ""),
            },
        )
        
        total_filled = 0
        total_failed = 0
        all_unmapped = []
        
        for page_num in range(MAX_FORM_PAGES):
            print(f"\n  === PAGE {page_num + 1} ===")
            
            self.app_logger.log_sync(
                job_id=self.job_id,
                action=LogAction.PAGE_LOADED,
                details={"url": page.url, "page_number": page_num + 1},
            )
            
            nav_attempts = 0
            result = None
            
            while nav_attempts < MAX_NAVIGATION_ATTEMPTS:
                result = self.process_page(page)
                
                if result.captcha_detected and result.paused:
                    total_filled += result.fields_filled
                    total_failed += result.fields_failed
                    all_unmapped.extend(result.unmapped_fields or [])
                    
                    print(f"  [PAUSED] CAPTCHA blocking. Filled {total_filled} fields total.")
                    
                    return FormFillingResult(
                        success=True,
                        page_number=page_num + 1,
                        fields_filled=total_filled,
                        fields_failed=total_failed,
                        needs_more_navigation=result.needs_more_navigation,
                        submit_ready=result.submit_ready,
                        captcha_detected=True,
                        captcha_type=result.captcha_type,
                        paused=True,
                        pause_reason=result.pause_reason,
                        unmapped_fields=all_unmapped,
                    )
                
                if result.error:
                    print(f"  [ERROR] {result.error}")
                    self.storage.set_session_status(self.job_id, "error", result.error)
                    self.app_logger.log_sync(
                        job_id=self.job_id,
                        action=LogAction.ERROR,
                        details={"error": result.error, "page_number": page_num + 1},
                    )
                    self.notifier.notify_job_failed(
                        job_id=self.job_id,
                        profile_id=self.profile_data.get("id"),
                        error=result.error,
                    )
                    return result
                
                if result.needs_more_navigation and result.fields_filled == 0:
                    print(f"  [NAV] Waiting for page load...")
                    try:
                        page.wait_for_load_state("networkidle", timeout=5000)
                    except Exception:
                        pass
                    nav_attempts += 1
                    continue
                
                break
            
            total_filled += result.fields_filled
            total_failed += result.fields_failed
            all_unmapped.extend(result.unmapped_fields or [])
            
            if result.submit_ready:
                print(f"  [READY] Application ready for submission!")
                print(f"  [READY] Total: {total_filled} filled, {total_failed} failed")
                
                self.storage.set_session_status(self.job_id, "ready_to_submit")
                self.app_logger.log_sync(
                    job_id=self.job_id,
                    action=LogAction.SUBMIT_READY,
                    details={
                        "fields_filled": total_filled,
                        "fields_failed": total_failed,
                        "pages_processed": page_num + 1,
                    },
                )
                self.notifier.notify_job_completed(
                    job_id=self.job_id,
                    profile_id=self.profile_data.get("id"),
                    fields_filled=total_filled,
                    submit_ready=True,
                )
                
                return FormFillingResult(
                    success=True,
                    page_number=page_num + 1,
                    fields_filled=total_filled,
                    fields_failed=total_failed,
                    needs_more_navigation=False,
                    submit_ready=True,
                    unmapped_fields=all_unmapped,
                )
            
            if result.needs_more_navigation and result.fields_filled > 0:
                print(f"  [NAV] Looking for next button...")
                
                ai_resp = self._last_ai_response
                next_clicked = False
                
                if ai_resp and ai_resp.next_button:
                    next_clicked = self._click_navigation_button(page, ai_resp.next_button, "next")
                
                if not next_clicked:
                    next_clicked = self._click_next_button_fallback(page)
                
                if next_clicked:
                    print(f"  [NAV] Clicked next, waiting for new page...")
                    try:
                        page.wait_for_load_state("networkidle", timeout=10000)
                    except Exception:
                        pass
                    continue
                else:
                    print(f"  [NAV] Could not find next button, stopping")
            
            break
        
        final_status = "completed" if total_filled > 0 else "incomplete"
        self.storage.set_session_status(self.job_id, final_status)
        
        self.app_logger.log_sync(
            job_id=self.job_id,
            action=LogAction.APPLICATION_COMPLETED if total_filled > 0 else LogAction.APPLICATION_FAILED,
            details={
                "success": total_filled > 0,
                "fields_filled": total_filled,
                "fields_failed": total_failed,
                "pages_processed": page_num + 1,
                "final_status": final_status,
            },
        )
        
        if total_filled > 0:
            self.notifier.notify_job_completed(
                job_id=self.job_id,
                profile_id=self.profile_data.get("id"),
                fields_filled=total_filled,
                submit_ready=False,
            )
        
        print(f"\n  [DONE] Application processing complete")
        print(f"  [DONE] Total: {total_filled} filled, {total_failed} failed, {page_num + 1} pages")
        
        return FormFillingResult(
            success=total_filled > 0,
            page_number=page_num + 1,
            fields_filled=total_filled,
            fields_failed=total_failed,
            needs_more_navigation=False,
            submit_ready=False,
            unmapped_fields=all_unmapped,
        )
