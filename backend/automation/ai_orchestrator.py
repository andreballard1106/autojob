import asyncio
import logging
import sys
import traceback
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass
from datetime import datetime
from typing import Dict, List, Optional, Tuple, Any

from app.config import settings
from automation.browser_manager import BrowserManager, BrowserSession
from automation.page_analyzer import PageAnalyzer, PageContent
from automation.ai_service import AIService, AIAnalysisResult
from automation.session_storage import SessionStorage, session_storage
from automation.form_filler import FormFiller, FormFillingResult

logger = logging.getLogger(__name__)


def _log_error(message: str, exc: Exception = None):
    """Log error to console with traceback."""
    print(f"[ORCHESTRATOR ERROR] {message}", flush=True)
    if exc:
        print(f"[ORCHESTRATOR ERROR] Exception: {exc}", flush=True)
        traceback.print_exc()
    sys.stdout.flush()


@dataclass
class JobProcessingResult:
    job_id: str
    success: bool
    page_content: Optional[PageContent] = None
    ai_response: Optional[AIAnalysisResult] = None
    fill_result: Optional[FormFillingResult] = None
    error: Optional[str] = None
    captcha_detected: bool = False
    paused: bool = False
    browser_kept_open: bool = False
    session_id: Optional[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        result = {
            "job_id": self.job_id,
            "success": self.success,
            "error": self.error,
            "fields_filled": self.fill_result.fields_filled if self.fill_result else 0,
            "fields_failed": self.fill_result.fields_failed if self.fill_result else 0,
            "submit_ready": self.fill_result.submit_ready if self.fill_result else False,
            "captcha_detected": self.captcha_detected,
            "paused": self.paused,
        }
        
        if self.fill_result:
            result["captcha_type"] = self.fill_result.captcha_type
            result["pause_reason"] = self.fill_result.pause_reason
        
        return result


class AIOrchestrator:
    def __init__(self, max_concurrent: int = None, headless: bool = None):
        self.max_concurrent = max_concurrent or settings.max_concurrent_browsers
        self.browser_manager = BrowserManager(max_browsers=self.max_concurrent, headless=headless)
        self.page_analyzer = PageAnalyzer()
        self.storage = session_storage
        self._executor = ThreadPoolExecutor(max_workers=self.max_concurrent + 5)
        
        self._ai_service: Optional[AIService] = None
        self._profiles_cache: Dict[str, Dict[str, Any]] = {}
        self._active_sessions: Dict[str, BrowserSession] = {}
    
    def set_ai_service(self, api_key: str, model: str = "gpt-4o") -> None:
        self._ai_service = AIService(api_key=api_key, model=model)
    
    def set_profile_data(self, profile_id: str, profile_data: Dict[str, Any]) -> None:
        self._profiles_cache[profile_id] = profile_data
    
    def set_headless(self, headless: bool) -> None:
        """Update browser headless setting."""
        self.browser_manager.set_headless(headless)
    
    async def initialize(self) -> None:
        await self.browser_manager.initialize()
        print(f"[OK] Orchestrator ready (max {self.max_concurrent} concurrent browsers)")
    
    async def shutdown(self) -> None:
        for job_id in list(self._active_sessions.keys()):
            self.close_job_browser(job_id)
        await self.browser_manager.shutdown()
        self._executor.shutdown(wait=False)
        self._profiles_cache.clear()
        self._active_sessions.clear()
        print("[OK] Orchestrator shut down")
    
    def has_active_browser(self, job_id: str) -> bool:
        return job_id in self._active_sessions
    
    def get_active_session(self, job_id: str) -> Optional[BrowserSession]:
        return self._active_sessions.get(job_id)
    
    def close_job_browser(self, job_id: str) -> bool:
        session = self._active_sessions.pop(job_id, None)
        if session:
            print(f"[{job_id[:8]}] Closing browser for job...")
            self.browser_manager._release_session_sync(session.session_id)
            return True
        return False
    
    def resume_job_processing(self, job_id: str, profile_id: str) -> Optional[JobProcessingResult]:
        session = self._active_sessions.get(job_id)
        if not session:
            return None
        
        short_id = job_id[:8]
        keep_browser_open = False
        profile_data = self._profiles_cache.get(profile_id, {})
        
        if not profile_data or not self._ai_service:
            return JobProcessingResult(
                job_id=job_id,
                success=False,
                error="Missing profile data or AI service",
            )
        
        try:
            page = session.page
            print(f"[{short_id}] Resuming job processing...")
            
            form_filler = FormFiller(
                driver=session.driver,
                ai_service=self._ai_service,
                profile_data=profile_data,
                job_id=job_id,
                storage=self.storage,
            )
            
            fill_result = form_filler.process_application(page)
            
            is_completed = fill_result.success and fill_result.submit_ready and not fill_result.captcha_detected
            
            if is_completed:
                print(f"[{short_id}] Application completed successfully after resume!")
                self.close_job_browser(job_id)
            else:
                keep_browser_open = True
                print(f"[{short_id}] Still in progress after resume - browser kept open")
            
            return JobProcessingResult(
                job_id=job_id,
                success=fill_result.success,
                fill_result=fill_result,
                captcha_detected=fill_result.captcha_detected,
                paused=fill_result.paused,
                browser_kept_open=keep_browser_open,
                session_id=session.session_id if keep_browser_open else None,
            )
            
        except Exception as e:
            print(f"[{short_id}] ERROR during resume: {e}")
            self.close_job_browser(job_id)
            return JobProcessingResult(
                job_id=job_id,
                success=False,
                error=str(e),
            )
    
    def get_active_browsers_count(self) -> int:
        return len(self._active_sessions)
    
    def get_active_job_ids(self) -> List[str]:
        return list(self._active_sessions.keys())
    
    def _open_and_extract_sync(
        self,
        job_id: str,
        url: str,
        profile_id: str = None,
    ) -> Tuple[str, bool, Optional[PageContent], Optional[str]]:
        short_id = job_id[:8]
        session = None
        
        try:
            print(f"[{short_id}] Creating browser...")
            session = self.browser_manager._acquire_session_sync(job_id)
            
            if not session:
                print(f"[{short_id}] ERROR: Failed to create browser")
                return (job_id, False, None, "Failed to create browser")
            
            print(f"[{short_id}] Browser created, navigating to: {url[:50]}...")
            page = session.page
            page.goto(url, wait_until="domcontentloaded", timeout=60000)
            print(f"[{short_id}] Page loaded")
            
            print(f"[{short_id}] Extracting content...")
            page_content = self.page_analyzer.analyze(page)
            print(f"[{short_id}] Extracted: {len(page_content.filtered_html)} chars, "
                  f"{len(page_content.inputs)} inputs, {len(page_content.buttons)} buttons")
            
            return (job_id, True, page_content, None)
            
        except Exception as e:
            print(f"[{short_id}] ERROR: {e}")
            return (job_id, False, None, str(e))
            
        finally:
            if session:
                print(f"[{short_id}] Closing browser...")
                self.browser_manager._release_session_sync(session.session_id)
    
    def _process_with_autofill_sync(
        self,
        job_id: str,
        url: str,
        profile_id: str,
    ) -> JobProcessingResult:
        short_id = job_id[:8]
        session = None
        keep_browser_open = False
        
        # ============================================
        # STEP 1: Validate Profile Data
        # ============================================
        print(f"\n{'='*70}")
        print(f"[{short_id}] STARTING JOB PROCESSING")
        print(f"{'='*70}")
        print(f"[{short_id}] Job ID: {job_id}")
        print(f"[{short_id}] URL: {url}")
        print(f"[{short_id}] Profile ID: {profile_id}")
        
        profile_data = self._profiles_cache.get(profile_id, {})
        if not profile_data:
            print(f"[{short_id}] ERROR: Profile data not found in cache!")
            print(f"[{short_id}] Available profiles: {list(self._profiles_cache.keys())}")
            return JobProcessingResult(
                job_id=job_id,
                success=False,
                error="Profile data not found",
            )
        
        print(f"[{short_id}] ✓ Profile loaded: {profile_data.get('first_name', '?')} {profile_data.get('last_name', '?')}")
        print(f"[{short_id}]   Email: {profile_data.get('email', 'N/A')}")
        print(f"[{short_id}]   Work Experience: {len(profile_data.get('work_experience', []))} entries")
        print(f"[{short_id}]   Education: {len(profile_data.get('education', []))} entries")
        print(f"[{short_id}]   Skills: {len(profile_data.get('skills', []))} skills")
        
        # ============================================
        # STEP 2: Validate AI Service
        # ============================================
        if not self._ai_service:
            print(f"[{short_id}] ERROR: AI service not configured!")
            return JobProcessingResult(
                job_id=job_id,
                success=False,
                error="AI service not configured",
            )
        
        print(f"[{short_id}] ✓ AI service configured (model: {self._ai_service.model})")
        
        # ============================================
        # STEP 3: Create Browser Session
        # ============================================
        try:
            print(f"\n[{short_id}] STEP 3: Creating browser session...")
            session = self.browser_manager._acquire_session_sync(job_id)
            
            if not session:
                print(f"[{short_id}] ERROR: Failed to create browser session!")
                return JobProcessingResult(
                    job_id=job_id,
                    success=False,
                    error="Failed to create browser",
                )
            
            print(f"[{short_id}] ✓ Browser session created: {session.session_id[:8]}...")
            
            # ============================================
            # STEP 4: Create Storage Session
            # ============================================
            print(f"\n[{short_id}] STEP 4: Creating storage session...")
            self.storage.create_session(job_id, profile_id, url)
            print(f"[{short_id}] ✓ Storage session created")
            
            # ============================================
            # STEP 5: Navigate to URL
            # ============================================
            print(f"\n[{short_id}] STEP 5: Navigating to URL...")
            print(f"[{short_id}] Target URL: {url}", flush=True)
            page = session.page
            page.goto(url, wait_until="domcontentloaded", timeout=60000)
            print(f"[{short_id}] ✓ DOM content loaded")
            
            # Wait for dynamic content to load
            print(f"[{short_id}] Waiting for network idle...", flush=True)
            try:
                page.wait_for_load_state("networkidle", timeout=10000)
                print(f"[{short_id}] ✓ Network idle reached")
            except Exception as e:
                print(f"[{short_id}] ⚠ Network idle timeout (page may still be loading): {e}")
            
            # Additional wait for JavaScript to execute
            import time
            print(f"[{short_id}] Waiting 2s for JavaScript execution...")
            time.sleep(2)
            
            print(f"\n[{short_id}] ✓ PAGE LOADED SUCCESSFULLY")
            print(f"[{short_id}]   Current URL: {page.url}")
            print(f"[{short_id}]   Page Title: {page.title if page.title else 'No title'}", flush=True)
            
            # ============================================
            # STEP 6: Create FormFiller
            # ============================================
            print(f"\n[{short_id}] STEP 6: Initializing FormFiller...")
            form_filler = FormFiller(
                driver=session.driver,
                ai_service=self._ai_service,
                profile_data=profile_data,
                job_id=job_id,
                storage=self.storage,
            )
            print(f"[{short_id}] ✓ FormFiller initialized")
            
            # ============================================
            # STEP 7: Process Application (Extract → AI → Fill)
            # ============================================
            print(f"\n[{short_id}] STEP 7: Processing application...")
            print(f"[{short_id}] This step will:")
            print(f"[{short_id}]   1. Extract page content (inputs, buttons, forms)")
            print(f"[{short_id}]   2. Filter HTML and prepare for AI")
            print(f"[{short_id}]   3. Send to OpenAI for field mapping")
            print(f"[{short_id}]   4. Execute autofill commands")
            print(f"[{short_id}]   5. Handle navigation (next/submit buttons)")
            fill_result = form_filler.process_application(page)
            
            is_completed = fill_result.success and fill_result.submit_ready and not fill_result.captcha_detected
            
            if is_completed:
                print(f"[{short_id}] Application completed successfully!")
            else:
                keep_browser_open = True
                self._active_sessions[job_id] = session
                
                if fill_result.captcha_detected or fill_result.paused:
                    print(f"[{short_id}] Waiting for user action - browser kept open")
                elif fill_result.submit_ready:
                    print(f"[{short_id}] Submit ready - browser kept open for confirmation")
                else:
                    print(f"[{short_id}] In progress (Filled={fill_result.fields_filled}, "
                          f"Failed={fill_result.fields_failed}) - browser kept open")
            
            return JobProcessingResult(
                job_id=job_id,
                success=fill_result.success,
                fill_result=fill_result,
                captcha_detected=fill_result.captcha_detected,
                paused=fill_result.paused,
                browser_kept_open=keep_browser_open,
                session_id=session.session_id if keep_browser_open else None,
            )
            
        except Exception as e:
            _log_error(f"[{short_id}] Job processing failed", e)
            self.storage.set_session_status(job_id, "error", str(e))
            return JobProcessingResult(
                job_id=job_id,
                success=False,
                error=str(e),
            )
            
        finally:
            if session and not keep_browser_open:
                print(f"[{short_id}] Closing browser...", flush=True)
                self.browser_manager._release_session_sync(session.session_id)
    
    def process_jobs_parallel_sync(
        self,
        jobs_data: List[Tuple[str, str]],
    ) -> Dict[str, Tuple[bool, Optional[PageContent], Optional[str]]]:
        print(f"\n[PARALLEL] Opening {len(jobs_data)} browsers simultaneously...")
        
        results = {}
        futures = {}
        
        for job_id, url in jobs_data:
            future = self._executor.submit(self._open_and_extract_sync, job_id, url)
            futures[future] = job_id
        
        for future in as_completed(futures):
            job_id, success, content, error = future.result()
            results[job_id] = (success, content, error)
        
        print(f"[PARALLEL] All {len(jobs_data)} browsers completed")
        return results
    
    def process_jobs_with_autofill_sync(
        self,
        jobs_data: List[Tuple[str, str, str]],
    ) -> Dict[str, JobProcessingResult]:
        print(f"\n[AUTOFILL] Processing {len(jobs_data)} jobs with AI autofill...")
        
        results = {}
        futures = {}
        
        for job_id, url, profile_id in jobs_data:
            future = self._executor.submit(
                self._process_with_autofill_sync,
                job_id,
                url,
                profile_id,
            )
            futures[future] = job_id
        
        for future in as_completed(futures):
            result = future.result()
            results[result.job_id] = result
        
        print(f"[AUTOFILL] All {len(jobs_data)} jobs completed")
        return results
    
    async def process_jobs_parallel(
        self,
        jobs_data: List[Tuple[str, str]],
    ) -> Dict[str, Tuple[bool, Optional[PageContent], Optional[str]]]:
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(None, self.process_jobs_parallel_sync, jobs_data)
    
    async def process_jobs_with_autofill(
        self,
        jobs_data: List[Tuple[str, str, str]],
    ) -> Dict[str, JobProcessingResult]:
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(None, self.process_jobs_with_autofill_sync, jobs_data)
