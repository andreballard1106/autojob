"""
Browser Manager - Handles Chrome browser lifecycle and session management

Uses Selenium WebDriver for browser automation (compatible with Python 3.13 on Windows).
"""

import asyncio
import logging
import os
import shutil
import tempfile
import threading
from concurrent.futures import ThreadPoolExecutor
from typing import Optional
from uuid import uuid4
import time

from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from webdriver_manager.chrome import ChromeDriverManager

from app.config import settings

logger = logging.getLogger(__name__)

# Thread pool for running sync browser operations
# Set to 30 to support 5+ concurrent browser sessions with headroom
# for async wrapper operations and nested calls
_executor = ThreadPoolExecutor(max_workers=30)

# Cache the ChromeDriver path
_driver_path = None


def _get_driver_path():
    """Get or download ChromeDriver path."""
    global _driver_path
    if _driver_path is None:
        logger.info("Downloading/locating ChromeDriver...")
        _driver_path = ChromeDriverManager().install()
        logger.info(f"ChromeDriver located at: {_driver_path}")
    return _driver_path


class BrowserSession:
    def __init__(
        self,
        session_id: str,
        driver: webdriver.Chrome,
        job_id: Optional[str] = None,
        is_busy: bool = False,
        user_data_dir: Optional[str] = None,
    ):
        self.session_id = session_id
        self.driver = driver
        self.job_id = job_id
        self.is_busy = is_busy
        self.created_at = time.time()
        self.user_data_dir = user_data_dir
        self._page_wrapper = None

    @property
    def page(self):
        if self._page_wrapper is None:
            self._page_wrapper = SeleniumPage(self.driver)
        return self._page_wrapper

    @property
    def context(self):
        return self.driver


class SeleniumPage:
    """Wrapper around Selenium WebDriver to provide Playwright-like API."""
    
    def __init__(self, driver: webdriver.Chrome):
        self.driver = driver
        self._default_timeout = settings.browser_timeout

    def goto(self, url: str, wait_until: str = "domcontentloaded", timeout: int = 30000):
        """Navigate to URL."""
        self.driver.set_page_load_timeout(timeout / 1000)
        self.driver.get(url)
        return self

    def wait_for_load_state(self, state: str = "domcontentloaded", timeout: int = None):
        """Wait for page load state."""
        if timeout is None:
            timeout = self._default_timeout * 1000
        
        wait = WebDriverWait(self.driver, timeout / 1000)
        if state == "networkidle":
            time.sleep(2)  # Approximate network idle
        else:
            wait.until(lambda d: d.execute_script("return document.readyState") == "complete")

    def wait_for_timeout(self, ms: int):
        """Wait for specified milliseconds."""
        time.sleep(ms / 1000)

    def wait_for_selector(self, selector: str, timeout: int = 5000, state: str = "visible"):
        """Wait for element matching selector."""
        wait = WebDriverWait(self.driver, timeout / 1000)
        by, value = self._parse_selector(selector)
        
        if state == "visible":
            return wait.until(EC.visibility_of_element_located((by, value)))
        else:
            return wait.until(EC.presence_of_element_located((by, value)))

    def query_selector(self, selector: str):
        """Find element by selector."""
        try:
            by, value = self._parse_selector(selector)
            elements = self.driver.find_elements(by, value)
            if elements:
                return SeleniumElement(elements[0], self.driver)
            return None
        except Exception:
            return None

    def query_selector_all(self, selector: str):
        """Find all elements by selector."""
        try:
            by, value = self._parse_selector(selector)
            elements = self.driver.find_elements(by, value)
            return [SeleniumElement(el, self.driver) for el in elements]
        except Exception:
            return []

    def text_content(self, selector: str) -> Optional[str]:
        """Get text content of element."""
        element = self.query_selector(selector)
        if element:
            return element.text_content()
        return None

    def content(self) -> str:
        """Get page HTML content."""
        return self.driver.page_source

    def screenshot(self, path: str = None, full_page: bool = False):
        """Take screenshot."""
        if path:
            self.driver.save_screenshot(path)
        else:
            return self.driver.get_screenshot_as_png()

    def close(self):
        """Close the page/tab."""
        pass  # Selenium driver.quit() handles this

    def set_default_timeout(self, timeout_ms: int):
        """Set default timeout."""
        self._default_timeout = timeout_ms / 1000

    @property
    def url(self) -> str:
        """Get current URL."""
        return self.driver.current_url

    @property
    def title(self) -> str:
        """Get page title."""
        return self.driver.title

    @property
    def keyboard(self):
        """Return keyboard interface."""
        return SeleniumKeyboard(self.driver)

    def locator(self, selector: str) -> "SeleniumLocator":
        """Return a locator for finding elements (Playwright-like API)."""
        return SeleniumLocator(self.driver, selector, self)
    
    def evaluate(self, js_code: str):
        """Execute JavaScript and return result."""
        return self.driver.execute_script(f"return ({js_code})()")

    def _parse_selector(self, selector: str):
        """Parse selector string to Selenium locator."""
        import re
        selector = selector.strip()
        
        # Handle xpath= prefix
        if selector.startswith("xpath="):
            return By.XPATH, selector[6:]
        
        # Handle text= prefix (Playwright-specific)
        if selector.startswith("text="):
            text = selector[5:].strip("'\"")
            return By.XPATH, f"//*[contains(text(), '{text}')]"
        
        # Handle text='...' format
        if selector.startswith("text='") or selector.startswith('text="'):
            text = selector[6:-1]
            return By.XPATH, f"//*[contains(text(), '{text}')]"
        
        # ID selector
        if selector.startswith("#"):
            return By.ID, selector[1:]
        
        # Class selector
        if selector.startswith(".") and " " not in selector and ":" not in selector:
            return By.CLASS_NAME, selector[1:]
        
        # Attribute selector [name='value']
        if selector.startswith("[") and "]" in selector:
            return By.CSS_SELECTOR, selector
        
        # :has-text() selector (Playwright-specific, convert to XPath)
        if ":has-text(" in selector:
            match = re.match(r"(.+?):has-text\(['\"](.+?)['\"]\)", selector)
            if match:
                tag = match.group(1) or "*"
                text = match.group(2)
                return By.XPATH, f"//{tag}[contains(text(), '{text}')]"
        
        # XPath
        if selector.startswith("//") or selector.startswith("("):
            return By.XPATH, selector
        
        # Default to CSS selector
        return By.CSS_SELECTOR, selector


class SeleniumElement:
    """Wrapper around Selenium WebElement to provide Playwright-like API."""
    
    def __init__(self, element, driver):
        self._element = element  # Use _element for access by external code
        self.element = element   # Keep for backwards compatibility
        self.driver = driver

    def scroll_into_view(self):
        """Scroll element into view."""
        self.driver.execute_script("arguments[0].scrollIntoView({block: 'center', behavior: 'smooth'});", self.element)
        time.sleep(0.3)  # Brief pause for smooth scrolling

    def clear(self):
        """Clear input content."""
        self.element.clear()

    def click(self):
        """Click the element."""
        self.element.click()

    def fill(self, value: str):
        """Fill input with value."""
        self.element.clear()
        self.element.send_keys(value)

    def type(self, value: str):
        """Type into element."""
        self.element.send_keys(value)

    def check(self):
        """Check checkbox."""
        if not self.element.is_selected():
            self.element.click()

    def uncheck(self):
        """Uncheck checkbox."""
        if self.element.is_selected():
            self.element.click()

    def is_checked(self) -> bool:
        """Check if checkbox is checked."""
        return self.element.is_selected()

    def is_visible(self) -> bool:
        """Check if element is visible."""
        return self.element.is_displayed()

    def get_attribute(self, name: str) -> Optional[str]:
        """Get element attribute."""
        return self.element.get_attribute(name)

    def text_content(self) -> str:
        """Get text content."""
        return self.element.text

    def evaluate(self, js: str):
        """Evaluate JavaScript on element."""
        return self.driver.execute_script(f"return (function(el) {{ return {js.replace('el =>', '')} }})(arguments[0])", self.element)

    def evaluate_handle(self, js: str):
        """Evaluate JavaScript and return handle."""
        result = self.driver.execute_script(f"return {js}", self.element)
        if result:
            return SeleniumElement(result, self.driver) if hasattr(result, 'tag_name') else result
        return None

    def select_option(self, value: str = None, label: str = None):
        """Select option in dropdown."""
        from selenium.webdriver.support.ui import Select
        select = Select(self.element)
        if label:
            select.select_by_visible_text(label)
        elif value:
            select.select_by_value(value)

    def set_input_files(self, file_path: str):
        """Set file input."""
        self.element.send_keys(os.path.abspath(file_path))

    def query_selector(self, selector: str):
        """Find child element."""
        try:
            page = SeleniumPage(self.driver)
            by, value = page._parse_selector(selector)
            elements = self.element.find_elements(by, value)
            if elements:
                return SeleniumElement(elements[0], self.driver)
            return None
        except Exception:
            return None

    def query_selector_all(self, selector: str):
        """Find all child elements."""
        try:
            page = SeleniumPage(self.driver)
            by, value = page._parse_selector(selector)
            elements = self.element.find_elements(by, value)
            return [SeleniumElement(el, self.driver) for el in elements]
        except Exception:
            return []


class SeleniumLocator:
    """Playwright-like locator for finding elements."""
    
    def __init__(self, driver, selector: str, page: "SeleniumPage"):
        self.driver = driver
        self.selector = selector
        self.page = page
        self._elements = None
    
    def _find_elements(self):
        """Find all matching elements."""
        if self._elements is None:
            by, value = self.page._parse_selector(self.selector)
            self._elements = self.driver.find_elements(by, value)
        return self._elements
    
    @property
    def first(self) -> Optional["SeleniumLocator"]:
        """Get first matching element as a locator."""
        elements = self._find_elements()
        if elements:
            locator = SeleniumLocator(self.driver, self.selector, self.page)
            locator._elements = [elements[0]]
            return locator
        return SeleniumLocator(self.driver, self.selector, self.page)
    
    def is_visible(self, timeout: int = None) -> bool:
        """Check if element is visible.
        
        Args:
            timeout: Optional timeout in milliseconds to wait for visibility
        """
        import time
        
        if timeout:
            # Wait up to timeout for element to be visible
            end_time = time.time() + (timeout / 1000.0)
            while time.time() < end_time:
                self._elements = None  # Force re-find
                elements = self._find_elements()
                if elements:
                    try:
                        if elements[0].is_displayed():
                            return True
                    except Exception:
                        pass
                time.sleep(0.1)
            return False
        else:
            elements = self._find_elements()
            if not elements:
                return False
            try:
                return elements[0].is_displayed()
            except Exception:
                return False
    
    def click(self):
        """Click the element."""
        elements = self._find_elements()
        if not elements:
            raise Exception(f"Element not found: {self.selector}")
        try:
            elements[0].click()
        except Exception as e:
            # Try JavaScript click as fallback
            self.driver.execute_script("arguments[0].click();", elements[0])
    
    def fill(self, value: str):
        """Fill input with value (clears first)."""
        elements = self._find_elements()
        if not elements:
            raise Exception(f"Element not found: {self.selector}")
        elements[0].clear()
        elements[0].send_keys(value)
    
    def type(self, value: str, delay: int = 0):
        """Type text character by character with optional delay (Playwright-like API).
        
        Args:
            value: Text to type
            delay: Delay between keystrokes in milliseconds
        """
        import time
        elements = self._find_elements()
        if not elements:
            raise Exception(f"Element not found: {self.selector}")
        element = elements[0]
        
        if delay > 0:
            # Type character by character with delay
            for char in str(value):
                element.send_keys(char)
                time.sleep(delay / 1000.0)  # Convert ms to seconds
        else:
            element.send_keys(value)
    
    def clear(self):
        """Clear the input field."""
        elements = self._find_elements()
        if not elements:
            raise Exception(f"Element not found: {self.selector}")
        elements[0].clear()
    
    def text_content(self) -> str:
        """Get text content of element."""
        elements = self._find_elements()
        if not elements:
            return ""
        return elements[0].text
    
    def get_attribute(self, name: str) -> Optional[str]:
        """Get attribute value."""
        elements = self._find_elements()
        if not elements:
            return None
        return elements[0].get_attribute(name)
    
    def is_checked(self) -> bool:
        """Check if checkbox/radio is checked."""
        elements = self._find_elements()
        if not elements:
            return False
        return elements[0].is_selected()
    
    def count(self) -> int:
        """Count matching elements."""
        return len(self._find_elements())


class SeleniumKeyboard:
    """Keyboard interface for Selenium."""
    
    def __init__(self, driver):
        self.driver = driver

    def press(self, key: str):
        """Press a key."""
        from selenium.webdriver.common.keys import Keys
        key_map = {
            "Escape": Keys.ESCAPE,
            "Enter": Keys.ENTER,
            "Tab": Keys.TAB,
        }
        active = self.driver.switch_to.active_element
        active.send_keys(key_map.get(key, key))


class BrowserManager:
    def __init__(self, max_browsers: int = None, headless: bool = None):
        self.max_browsers = max_browsers or settings.max_concurrent_browsers
        # Use passed headless param, or fall back to config setting
        self.headless = headless if headless is not None else settings.browser_headless
        self._sessions: dict[str, BrowserSession] = {}
        self._lock = threading.Lock()
        self._initialized = False
        self._creating_count = 0

    def set_headless(self, headless: bool) -> None:
        """Update headless setting (for database settings)."""
        self.headless = headless
        print(f"[BROWSER] Headless mode set to: {headless}")

    def _create_driver(self) -> tuple[webdriver.Chrome, str]:
        logger.info("Creating Chrome WebDriver instance...")
        
        user_data_dir = tempfile.mkdtemp(prefix="chrome_session_")
        logger.info(f"Using temp user data dir: {user_data_dir}")
        
        options = Options()
        options.add_argument(f"--user-data-dir={user_data_dir}")
        
        if self.headless:
            print("[BROWSER] Running in HEADLESS mode", flush=True)
            logger.info("Running in headless mode")
            options.add_argument("--headless=new")
        else:
            print("[BROWSER] Running in VISIBLE mode (browser window will appear)", flush=True)
            logger.info("Running in visible mode (headless=False)")
        
        options.add_argument("--disable-blink-features=AutomationControlled")
        options.add_argument("--disable-dev-shm-usage")
        options.add_argument("--no-sandbox")
        options.add_argument("--window-size=1280,800")
        options.add_argument("--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36")
        options.add_experimental_option("excludeSwitches", ["enable-automation"])
        options.add_experimental_option("useAutomationExtension", False)
        
        try:
            driver_path = _get_driver_path()
            logger.info(f"Using ChromeDriver at: {driver_path}")
            service = Service(driver_path)
            driver = webdriver.Chrome(service=service, options=options)
            logger.info("Chrome WebDriver created successfully")
        except Exception as e:
            logger.error(f"Failed to create Chrome WebDriver: {e}")
            shutil.rmtree(user_data_dir, ignore_errors=True)
            import traceback
            traceback.print_exc()
            raise
        
        driver.set_page_load_timeout(settings.browser_timeout)
        driver.implicitly_wait(5)
        
        return driver, user_data_dir

    def _init_sync(self) -> None:
        """Initialize the browser manager."""
        if self._initialized:
            return
        
        logger.info("Initializing browser manager...")
        
        # Pre-download ChromeDriver
        _get_driver_path()
        
        self._initialized = True
        logger.info(f"Browser manager initialized (max sessions: {self.max_browsers})")

    async def initialize(self) -> None:
        """Initialize the browser manager."""
        if self._initialized:
            return
        
        loop = asyncio.get_event_loop()
        await loop.run_in_executor(_executor, self._init_sync)

    def _shutdown_sync(self) -> None:
        """Shutdown synchronously."""
        logger.info("Shutting down browser manager...")

        with self._lock:
            for session in list(self._sessions.values()):
                self._close_session_sync(session)
            self._sessions.clear()

        self._initialized = False
        logger.info("Browser manager shut down")

    async def shutdown(self) -> None:
        """Clean up all browser resources."""
        loop = asyncio.get_event_loop()
        await loop.run_in_executor(_executor, self._shutdown_sync)

    def _acquire_session_sync(self, job_id: str) -> Optional[BrowserSession]:
        if not self._initialized:
            with self._lock:
                if not self._initialized:
                    self._init_sync()
        
        with self._lock:
            active = sum(1 for s in self._sessions.values() if s.is_busy)
            total_in_progress = active + self._creating_count
            
            if total_in_progress >= self.max_browsers:
                logger.warning(f"Max sessions reached ({total_in_progress}/{self.max_browsers})")
                return None
            
            self._creating_count += 1
        
        session_id = str(uuid4())
        user_data_dir = None
        
        try:
            import sys
            print(f"[BROWSER] Creating new browser for job {job_id[:8]}...", flush=True)
            sys.stdout.flush()
            driver, user_data_dir = self._create_driver()
            print(f"[BROWSER] Browser created for job {job_id[:8]}", flush=True)
            sys.stdout.flush()
            
            session = BrowserSession(
                session_id=session_id,
                driver=driver,
                job_id=job_id,
                is_busy=True,
                user_data_dir=user_data_dir,
            )
            
            with self._lock:
                self._sessions[session_id] = session
                self._creating_count -= 1
            
            return session
            
        except Exception as e:
            print(f"[BROWSER ERROR] Failed to create browser: {e}", flush=True)
            logger.error(f"Failed to create browser: {e}")
            import traceback
            traceback.print_exc()
            import sys
            sys.stdout.flush()
            with self._lock:
                self._creating_count -= 1
            if user_data_dir:
                shutil.rmtree(user_data_dir, ignore_errors=True)
            return None

    async def acquire_session(self, job_id: str) -> Optional[BrowserSession]:
        """Acquire a browser session for a job application."""
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(_executor, self._acquire_session_sync, job_id)

    def _release_session_sync(self, session_id: str, close: bool = True) -> None:
        """Release session synchronously."""
        with self._lock:
            session = self._sessions.get(session_id)
            if not session:
                return

            session.is_busy = False

            if close:
                self._close_session_sync(session)
                del self._sessions[session_id]

            logger.info(f"Released session {session_id}")

    async def release_session(self, session_id: str, close: bool = True) -> None:
        """Release a browser session."""
        loop = asyncio.get_event_loop()
        await loop.run_in_executor(_executor, self._release_session_sync, session_id, close)

    def _close_session_sync(self, session: BrowserSession) -> None:
        try:
            session.driver.quit()
        except Exception as e:
            logger.error(f"Error closing session {session.session_id}: {e}")
        
        if session.user_data_dir and os.path.exists(session.user_data_dir):
            try:
                shutil.rmtree(session.user_data_dir, ignore_errors=True)
                logger.debug(f"Cleaned up temp dir: {session.user_data_dir}")
            except Exception as e:
                logger.warning(f"Failed to clean temp dir: {e}")

    def _take_screenshot_sync(self, session_id: str, name: str = "screenshot") -> Optional[str]:
        """Take screenshot synchronously."""
        session = self._sessions.get(session_id)
        if not session:
            return None

        # Create screenshots directory
        screenshot_dir = os.path.join(settings.storage_path, "screenshots")
        os.makedirs(screenshot_dir, exist_ok=True)

        # Generate filename
        filename = f"{session.job_id}_{name}_{session_id[:8]}.png"
        filepath = os.path.join(screenshot_dir, filename)

        try:
            session.driver.save_screenshot(filepath)
            logger.debug(f"Screenshot saved: {filepath}")
            return filepath
        except Exception as e:
            logger.error(f"Failed to take screenshot: {e}")
            return None

    async def take_screenshot(
        self,
        session_id: str,
        name: str = "screenshot",
    ) -> Optional[str]:
        """Take a screenshot of the current page."""
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(_executor, self._take_screenshot_sync, session_id, name)

    def get_session(self, session_id: str) -> Optional[BrowserSession]:
        """Get a session by ID."""
        return self._sessions.get(session_id)

    def get_session_by_job(self, job_id: str) -> Optional[BrowserSession]:
        """Get a session by job ID."""
        for session in self._sessions.values():
            if session.job_id == job_id:
                return session
        return None

    @property
    def active_session_count(self) -> int:
        """Get count of active (busy) sessions."""
        return sum(1 for s in self._sessions.values() if s.is_busy)

    @property
    def available_slots(self) -> int:
        """Get number of available session slots."""
        return max(0, self.max_browsers - self.active_session_count)
