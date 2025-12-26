"""
Default workflow handler for job application automation.

This handler uses AI-based analysis and works with any job platform.
It serves as the fallback when no platform-specific handler is available.
"""

import logging
import time
import traceback
from typing import Any, Dict, List, Optional, Tuple

from autofill import AutofillEngine
from autofill.models import FillResult
from automation.workflows.base import BaseWorkflowHandler, WorkflowResult
from automation.page_analyzer import PageAnalyzer, PageContent
from automation.captcha_detector import CaptchaDetectionResult
from automation.application_logger import LogAction

logger = logging.getLogger(__name__)

# Maximum number of form pages to process in a multi-page application
MAX_FORM_PAGES = 10


class DefaultWorkflowHandler(BaseWorkflowHandler):
    """
    Default workflow handler using AI-based page analysis.
    
    This handler works with any job application platform by using
    OpenAI to analyze page structure and generate autofill commands.
    
    Platform-specific handlers can extend this class or BaseWorkflowHandler
    to provide optimized behavior for specific ATS platforms.
    """
    
    PLATFORM_NAME = "default"
    URL_PATTERNS = []  # Matches nothing - used as fallback
    
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
        
        # Configure autofill engine: no retries for now
        self.autofill_engine.configure(
            stop_on_error=False,
            retry_count=0,
            retry_delay_ms=0,
        )
    
    def process_page(self, page) -> WorkflowResult:
        """Process a single page: extract content, call AI, execute autofill."""
        try:
            self.pre_process_hook(page)
            result = self._process_page_internal(page)
            return self.post_process_hook(page, result)
        except Exception as e:
            self._log(f"Error processing page: {e}", "error")
            traceback.print_exc()
            return WorkflowResult(
                success=False,
                page_number=0,
                fields_filled=0,
                fields_failed=0,
                needs_more_navigation=False,
                submit_ready=False,
                error=f"Page processing error: {str(e)}",
                platform=self.PLATFORM_NAME,
            )
    
    def _process_page_internal(self, page) -> WorkflowResult:
        """Internal page processing with error handling at caller."""
        short_id = self.job_id[:8]
        
        # ============================================
        # STEP 1: Extract Page Content
        # ============================================
        self._log(f"Extracting page content...")
        page_content = self._extract_page_content(page)
        
        # ============================================
        # STEP 2: Save Page Snapshot
        # ============================================
        if self.storage:
            self.storage.add_page_snapshot(self.job_id, page_content.to_dict())
            self._log(f"Page snapshot saved")
        
        # ============================================
        # STEP 3: Check for CAPTCHA
        # ============================================
        self._log(f"Checking for CAPTCHA...")
        captcha_result = self._check_for_captcha(page, page_content)
        has_captcha = captcha_result.detected
        
        if has_captcha:
            self._log(f"⚠ CAPTCHA DETECTED: {captcha_result.captcha_type}", "warning")
        else:
            self._log(f"✓ No CAPTCHA detected")
        
        # ============================================
        # STEP 4: Call OpenAI for Analysis
        # ============================================
        self._log(f"Calling OpenAI to analyze page...")
        ai_response = self.ai_service.analyze_and_generate_commands_sync(
            page_content.to_dict(),
            self.profile_data,
        )
        self._last_ai_response = ai_response
        
        platform = ai_response.platform if hasattr(ai_response, 'platform') else "unknown"
        self._log(f"AI Response: platform={platform}, page_type={ai_response.page_type}, "
                  f"is_form={ai_response.is_form_page}")
        
        # ============================================
        # STEP 5: Execute Autofill Commands
        # ============================================
        filled = 0
        failed = 0
        results = []
        
        if ai_response.is_form_page and ai_response.field_mappings:
            results, filled, failed = self._execute_autofill_commands(ai_response)
            self._save_autofill_results(results, ai_response)
        
        session = self.storage.get_session(self.job_id) if self.storage else None
        page_number = session.current_page if session else 1
        
        has_next = ai_response.next_button is not None
        has_submit = ai_response.submit_button is not None
        has_apply = ai_response.apply_button is not None
        
        # Handle CAPTCHA
        if has_captcha:
            return self._handle_captcha_pause(
                page=page,
                captcha_result=captcha_result,
                fields_filled=filled,
                fields_failed=failed,
                page_number=page_number,
                ai_response=ai_response,
            )
        
        # Handle non-form pages
        if not ai_response.is_form_page and not ai_response.field_mappings:
            page_type = ai_response.page_type
            self._log(f"Page is not a form page (type: {page_type})")
            
            # Job listing page
            if page_type == "job_listing" or has_apply:
                self._log(f"Job listing page - need to click Apply button")
                return WorkflowResult(
                    success=True,
                    page_number=page_number,
                    fields_filled=0,
                    fields_failed=0,
                    needs_more_navigation=True,
                    submit_ready=False,
                    platform=platform,
                )
            
            # Confirmation page
            if page_type == "confirmation":
                self._log(f"Confirmation page - application submitted")
                return WorkflowResult(
                    success=True,
                    page_number=page_number,
                    needs_more_navigation=False,
                    submit_ready=True,
                    platform=platform,
                )
            
            # Review page
            if page_type == "review_page" and has_submit:
                self._log(f"Review page - ready to submit")
                return WorkflowResult(
                    success=True,
                    page_number=page_number,
                    needs_more_navigation=False,
                    submit_ready=True,
                    platform=platform,
                )
            
            # Has navigation buttons
            if has_next or has_submit:
                return WorkflowResult(
                    success=True,
                    page_number=page_number,
                    needs_more_navigation=True,
                    submit_ready=False,
                    platform=platform,
                )
            
            # No form and no navigation
            return WorkflowResult(
                success=False,
                page_number=page_number,
                error=f"Page type '{page_type}' with no form fields or navigation buttons.",
                platform=platform,
            )
        
        return WorkflowResult(
            success=filled > 0 or failed == 0,
            page_number=page_number,
            fields_filled=filled,
            fields_failed=failed,
            needs_more_navigation=has_next,
            submit_ready=has_submit and not has_next,
            unmapped_fields=ai_response.unmapped_fields,
            platform=platform,
        )
    
    def process_application(self, page) -> WorkflowResult:
        """Process entire job application (potentially multi-page)."""
        try:
            return self._process_application_internal(page)
        except Exception as e:
            self._log(f"Error processing application: {e}", "error")
            traceback.print_exc()
            if self.storage:
                self.storage.set_session_status(self.job_id, "error", str(e))
            if self.app_logger:
                self.app_logger.log_sync(
                    job_id=self.job_id,
                    action=LogAction.ERROR,
                    details={"error": str(e)},
                )
            return WorkflowResult(
                success=False,
                error=f"Application processing error: {str(e)}",
                platform=self.PLATFORM_NAME,
            )
    
    def _process_application_internal(self, page) -> WorkflowResult:
        """Internal application processing."""
        
        # Initialize session
        if self.storage:
            session = self.storage.get_session(self.job_id)
            if not session:
                session = self.storage.create_session(
                    job_id=self.job_id,
                    profile_id=self.profile_data.get("id", ""),
                    url=page.url,
                )
        
        if self.app_logger:
            self.app_logger.log_sync(
                job_id=self.job_id,
                action=LogAction.PROCESSING_STARTED,
                details={"url": page.url, "profile_id": self.profile_data.get("id", "")},
            )
        
        total_filled = 0
        total_failed = 0
        all_unmapped = []
        detected_platform = "unknown"
        
        # Track processed pages to prevent infinite loops
        processed_pages = set()
        consecutive_no_progress = 0
        max_no_progress = 3
        
        for page_num in range(MAX_FORM_PAGES):
            current_url = page.url
            
            # Create page signature
            try:
                page_title = page.title() if callable(getattr(page, 'title', None)) else str(page.title)
                input_count = page.locator("input:visible, select:visible, textarea:visible").count()
                page_signature = f"{page_title}_{input_count}"
            except Exception:
                page_signature = "unknown"
            
            page_key = (current_url, page_signature)
            
            # Check for duplicate processing
            if page_key in processed_pages:
                self._log(f"Page already processed, stopping")
                break
            
            self._log(f"=== PAGE {page_num + 1} ===")
            self._log(f"URL: {current_url[:60]}...")
            
            processed_pages.add(page_key)
            
            if self.app_logger:
                self.app_logger.log_sync(
                    job_id=self.job_id,
                    action=LogAction.PAGE_LOADED,
                    details={"url": current_url, "page_number": page_num + 1},
                )
            
            # Process page
            result = self.process_page(page)
            
            # Update detected platform
            if result.platform and result.platform != "unknown":
                detected_platform = result.platform
            
            # Handle CAPTCHA
            if result.captcha_detected and result.paused:
                total_filled += result.fields_filled
                total_failed += result.fields_failed
                all_unmapped.extend(result.unmapped_fields or [])
                
                self._log(f"CAPTCHA blocking. Filled {total_filled} fields total.")
                return WorkflowResult(
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
                    platform=detected_platform,
                )
            
            # Handle error
            if result.error:
                self._log(f"Error: {result.error}", "error")
                if self.storage:
                    self.storage.set_session_status(self.job_id, "error", result.error)
                if self.notifier:
                    self.notifier.notify_job_failed(
                        job_id=self.job_id,
                        profile_id=self.profile_data.get("id"),
                        error=result.error,
                    )
                return result
            
            total_filled += result.fields_filled
            total_failed += result.fields_failed
            all_unmapped.extend(result.unmapped_fields or [])
            
            # Track progress
            if result.fields_filled == 0 and not result.submit_ready:
                consecutive_no_progress += 1
                if consecutive_no_progress >= max_no_progress:
                    self._log(f"No progress for {max_no_progress} pages, stopping")
                    break
            else:
                consecutive_no_progress = 0
            
            # Submit ready
            if result.submit_ready:
                self._log(f"Application ready for submission! Total: {total_filled} filled")
                if self.storage:
                    self.storage.set_session_status(self.job_id, "ready_to_submit")
                if self.notifier:
                    self.notifier.notify_job_completed(
                        job_id=self.job_id,
                        profile_id=self.profile_data.get("id"),
                        fields_filled=total_filled,
                        submit_ready=True,
                    )
                
                return WorkflowResult(
                    success=True,
                    page_number=page_num + 1,
                    fields_filled=total_filled,
                    fields_failed=total_failed,
                    needs_more_navigation=False,
                    submit_ready=True,
                    unmapped_fields=all_unmapped,
                    platform=detected_platform,
                )
            
            # Navigate to next page
            if result.needs_more_navigation:
                nav_clicked = self._handle_navigation(page, result)
                
                if nav_clicked:
                    self._log(f"Navigation clicked, waiting for page load...")
                    try:
                        page.wait_for_load_state("networkidle", timeout=10000)
                    except Exception:
                        pass
                    time.sleep(1)
                    continue
                else:
                    self._log(f"Could not navigate, stopping")
                    break
            
            self._log(f"Page processed, no more navigation needed")
            break
        
        # Final status
        final_status = "completed" if total_filled > 0 else "incomplete"
        if self.storage:
            self.storage.set_session_status(self.job_id, final_status)
        
        if self.app_logger:
            self.app_logger.log_sync(
                job_id=self.job_id,
                action=LogAction.APPLICATION_COMPLETED if total_filled > 0 else LogAction.APPLICATION_FAILED,
                details={"fields_filled": total_filled, "fields_failed": total_failed},
            )
        
        if total_filled > 0 and self.notifier:
            self.notifier.notify_job_completed(
                job_id=self.job_id,
                profile_id=self.profile_data.get("id"),
                fields_filled=total_filled,
                submit_ready=False,
            )
        
        self._log(f"Application complete. Total: {total_filled} filled, {total_failed} failed")
        
        return WorkflowResult(
            success=total_filled > 0,
            page_number=page_num + 1,
            fields_filled=total_filled,
            fields_failed=total_failed,
            needs_more_navigation=False,
            submit_ready=False,
            unmapped_fields=all_unmapped,
            platform=detected_platform,
        )
    
    # =========================================================================
    # Helper Methods
    # =========================================================================
    
    def _extract_page_content(self, page) -> PageContent:
        """Extract and filter page content for AI analysis."""
        return self.page_analyzer.analyze(page)
    
    def _check_for_captcha(self, page, page_content: PageContent) -> CaptchaDetectionResult:
        """Check if CAPTCHA is present on page."""
        if self.captcha_detector:
            page_result = self.captcha_detector.detect_from_page(page)
            if page_result.detected:
                return page_result
            return self.captcha_detector.detect_from_html(page_content.filtered_html)
        
        # No detector available
        from automation.captcha_detector import CaptchaDetectionResult
        return CaptchaDetectionResult(detected=False)
    
    def _execute_autofill_commands(self, ai_response) -> Tuple[List[FillResult], int, int]:
        """Execute autofill commands from AI response."""
        if not ai_response.field_mappings:
            return [], 0, 0
        
        self._log(f"Executing {len(ai_response.field_mappings)} autofill commands...")
        
        commands = []
        for mapping in ai_response.field_mappings:
            cmd = mapping.to_autofill_command()
            commands.append(cmd)
        
        results = self.autofill_engine.execute_all(commands)
        
        filled = sum(1 for r in results if r.success)
        failed = sum(1 for r in results if not r.success)
        
        self._log(f"Autofill result: {filled} filled, {failed} failed")
        return results, filled, failed
    
    def _save_autofill_results(self, results: List[FillResult], ai_response) -> None:
        """Save autofill results to session storage."""
        if not self.storage:
            return
        
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
            
            if self.app_logger:
                self.app_logger.log_sync(
                    job_id=self.job_id,
                    action=LogAction.FIELD_FILLED if result.success else LogAction.FIELD_FAILED,
                    details={
                        "field_name": field_name,
                        "selector": result.selector,
                        "success": result.success,
                        "error": result.error,
                    },
                )
        
        self.storage.add_autofill_results(self.job_id, result_dicts)
    
    def _handle_captcha_pause(
        self,
        page,
        captcha_result: CaptchaDetectionResult,
        fields_filled: int,
        fields_failed: int,
        page_number: int,
        ai_response,
    ) -> WorkflowResult:
        """Handle CAPTCHA detection - pause for user action."""
        self._log(f"CAPTCHA detected: {captcha_result.captcha_type}")
        
        current_url = ""
        try:
            current_url = page.url
        except Exception:
            pass
        
        if self.app_logger:
            self.app_logger.log_sync(
                job_id=self.job_id,
                action=LogAction.CAPTCHA_DETECTED,
                details={
                    "captcha_type": captcha_result.captcha_type,
                    "fields_filled": fields_filled,
                    "url": current_url,
                },
            )
        
        if self.notifier:
            self.notifier.notify_captcha_detected(
                job_id=self.job_id,
                profile_id=self.profile_data.get("id"),
                captcha_type=captcha_result.captcha_type,
                url=current_url,
            )
        
        if self.storage:
            self.storage.set_session_status(
                self.job_id,
                "captcha_waiting",
                f"CAPTCHA detected ({captcha_result.captcha_type}). Waiting for user.",
            )
        
        platform = ai_response.platform if hasattr(ai_response, 'platform') else "unknown"
        has_next = ai_response.next_button is not None if ai_response else False
        has_submit = ai_response.submit_button is not None if ai_response else False
        
        return WorkflowResult(
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
            platform=platform,
        )
    
    def _handle_navigation(self, page, result: WorkflowResult) -> bool:
        """Handle navigation between pages."""
        ai_resp = self._last_ai_response
        page_type = ai_resp.page_type if ai_resp else "unknown"
        
        # Strategy 1: For job listing pages, try Apply button
        if page_type == "job_listing" or (result.fields_filled == 0 and ai_resp and ai_resp.apply_button):
            self._log(f"Trying Apply button...")
            if ai_resp and ai_resp.apply_button:
                if self._click_navigation_button(page, ai_resp.apply_button, "apply"):
                    return True
            if self._try_click_apply_button(page):
                return True
        
        # Strategy 2: Try Next button
        if ai_resp and ai_resp.next_button:
            self._log(f"Trying Next button...")
            if self._click_navigation_button(page, ai_resp.next_button, "next"):
                return True
        
        # Strategy 3: Fallback patterns
        self._log(f"Trying fallback navigation patterns...")
        if self._click_next_button_fallback(page):
            return True
        
        # Strategy 4: Try Apply as last resort for no-field pages
        if result.fields_filled == 0:
            if self._try_click_apply_button(page):
                return True
        
        return False
    
    def _click_navigation_button(self, page, button_info: Dict, button_type: str = "next") -> bool:
        """Click a navigation button using AI-detected selector."""
        if not button_info:
            return False
        
        selector = button_info.get('selector', '')
        selector_type = button_info.get('selector_type', 'css')
        
        if not selector:
            return False
        
        try:
            if selector_type == 'xpath':
                locator = page.locator(f"xpath={selector}")
            else:
                locator = page.locator(selector)
            
            btn = locator.first
            if btn.is_visible():
                btn.click()
                self._log(f"Clicked {button_type} button: {selector[:40]}...")
                return True
        except Exception as e:
            self._log(f"Failed to click {button_type} button: {e}", "warning")
        
        return False
    
    def _try_click_apply_button(self, page) -> bool:
        """Try to find and click common Apply/Start buttons."""
        patterns = [
            "button:has-text('Apply')",
            "button:has-text('Apply Now')",
            "button:has-text('Apply for this job')",
            "a:has-text('Apply')",
            "a:has-text('Apply Now')",
            "[data-automation-id='jobPostingApplyButton']",
            "[data-testid='apply-button']",
            "button:has-text('Start Application')",
            "button:has-text('Start')",
            "button:has-text('Begin Application')",
        ]
        
        for pattern in patterns:
            try:
                locator = page.locator(pattern)
                if locator.first and locator.first.is_visible():
                    locator.first.click()
                    self._log(f"Clicked Apply button: {pattern}")
                    return True
            except Exception:
                continue
        
        return False
    
    def _click_next_button_fallback(self, page) -> bool:
        """Try common next button patterns."""
        patterns = [
            "button:has-text('Next')",
            "button:has-text('Continue')",
            "button:has-text('Save and Continue')",
            "[data-automation-id='bottom-navigation-next-button']",
            "input[type='submit'][value*='Next']",
            "input[type='submit'][value*='Continue']",
        ]
        
        for pattern in patterns:
            try:
                btn = page.locator(pattern).first
                if btn.is_visible():
                    btn.click()
                    self._log(f"Clicked fallback next button: {pattern}")
                    return True
            except Exception:
                continue
        
        return False

