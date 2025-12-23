import time
from typing import Optional, List, Callable

from selenium.webdriver.remote.webdriver import WebDriver
from selenium.webdriver.remote.webelement import WebElement
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import StaleElementReferenceException

from autofill.models import SelectorType
from autofill.exceptions import ElementNotFoundError


class ElementLocator:
    def __init__(self, driver: WebDriver):
        self.driver = driver
        self._iframe_stack: List[WebElement] = []
    
    def _get_by(self, selector_type: SelectorType) -> str:
        mapping = {
            SelectorType.CSS: By.CSS_SELECTOR,
            SelectorType.XPATH: By.XPATH,
            SelectorType.ID: By.ID,
            SelectorType.NAME: By.NAME,
        }
        return mapping.get(selector_type, By.CSS_SELECTOR)
    
    def find(
        self,
        selector: str,
        selector_type: SelectorType = SelectorType.CSS,
        timeout_ms: int = 10000,
        raise_on_not_found: bool = True,
    ) -> Optional[WebElement]:
        by = self._get_by(selector_type)
        timeout_sec = timeout_ms / 1000
        
        try:
            wait = WebDriverWait(self.driver, timeout_sec)
            element = wait.until(EC.presence_of_element_located((by, selector)))
            return element
        except Exception:
            if raise_on_not_found:
                raise ElementNotFoundError(selector, selector_type.value)
            return None
    
    def find_clickable(
        self,
        selector: str,
        selector_type: SelectorType = SelectorType.CSS,
        timeout_ms: int = 10000,
    ) -> WebElement:
        by = self._get_by(selector_type)
        timeout_sec = timeout_ms / 1000
        
        try:
            wait = WebDriverWait(self.driver, timeout_sec)
            element = wait.until(EC.element_to_be_clickable((by, selector)))
            return element
        except Exception:
            raise ElementNotFoundError(selector, selector_type.value)
    
    def find_visible(
        self,
        selector: str,
        selector_type: SelectorType = SelectorType.CSS,
        timeout_ms: int = 10000,
    ) -> WebElement:
        by = self._get_by(selector_type)
        timeout_sec = timeout_ms / 1000
        
        try:
            wait = WebDriverWait(self.driver, timeout_sec)
            element = wait.until(EC.visibility_of_element_located((by, selector)))
            return element
        except Exception:
            raise ElementNotFoundError(selector, selector_type.value)
    
    def find_all(
        self,
        selector: str,
        selector_type: SelectorType = SelectorType.CSS,
    ) -> List[WebElement]:
        by = self._get_by(selector_type)
        return self.driver.find_elements(by, selector)
    
    def find_with_retry(
        self,
        selector: str,
        selector_type: SelectorType = SelectorType.CSS,
        timeout_ms: int = 10000,
        retries: int = 1,  # Default: single attempt (no retries)
    ) -> WebElement:
        last_error = None
        for _ in range(retries):
            try:
                return self.find(selector, selector_type, timeout_ms)
            except (ElementNotFoundError, StaleElementReferenceException) as e:
                last_error = e
                if retries > 1:
                    time.sleep(0.5)  # Only sleep if actually retrying
        raise last_error or ElementNotFoundError(selector, selector_type.value)
    
    def find_in_iframe(
        self,
        iframe_selector: str,
        element_selector: str,
        selector_type: SelectorType = SelectorType.CSS,
        timeout_ms: int = 10000,
    ) -> WebElement:
        iframe = self.find(iframe_selector, selector_type, timeout_ms)
        self.driver.switch_to.frame(iframe)
        self._iframe_stack.append(iframe)
        
        try:
            return self.find(element_selector, selector_type, timeout_ms)
        except Exception:
            self.exit_iframe()
            raise
    
    def exit_iframe(self) -> None:
        if self._iframe_stack:
            self._iframe_stack.pop()
        self.driver.switch_to.default_content()
        for iframe in self._iframe_stack:
            try:
                self.driver.switch_to.frame(iframe)
            except Exception:
                pass
    
    def exit_all_iframes(self) -> None:
        self._iframe_stack.clear()
        self.driver.switch_to.default_content()
    
    def find_by_text(
        self,
        text: str,
        tag: str = "*",
        exact: bool = False,
        timeout_ms: int = 10000,
    ) -> WebElement:
        if exact:
            xpath = f"//{tag}[normalize-space(text())='{text}']"
        else:
            xpath = f"//{tag}[contains(normalize-space(text()), '{text}')]"
        return self.find(xpath, SelectorType.XPATH, timeout_ms)
    
    def find_by_label(
        self,
        label_text: str,
        exact: bool = False,
        timeout_ms: int = 10000,
    ) -> WebElement:
        if exact:
            label_xpath = f"//label[normalize-space(text())='{label_text}']"
        else:
            label_xpath = f"//label[contains(normalize-space(text()), '{label_text}')]"
        
        try:
            label = self.find(label_xpath, SelectorType.XPATH, timeout_ms)
            for_attr = label.get_attribute("for")
            
            if for_attr:
                return self.find(f"#{for_attr}", SelectorType.CSS, timeout_ms)
            
            input_el = label.find_element(By.XPATH, ".//input | .//select | .//textarea")
            if input_el:
                return input_el
        except Exception:
            pass
        
        raise ElementNotFoundError(f"label:{label_text}", "label")
    
    def find_by_placeholder(
        self,
        placeholder: str,
        exact: bool = False,
        timeout_ms: int = 10000,
    ) -> WebElement:
        if exact:
            selector = f"input[placeholder='{placeholder}'], textarea[placeholder='{placeholder}']"
        else:
            selector = f"input[placeholder*='{placeholder}'], textarea[placeholder*='{placeholder}']"
        return self.find(selector, SelectorType.CSS, timeout_ms)
    
    def find_by_aria_label(
        self,
        aria_label: str,
        exact: bool = False,
        timeout_ms: int = 10000,
    ) -> WebElement:
        if exact:
            selector = f"[aria-label='{aria_label}']"
        else:
            selector = f"[aria-label*='{aria_label}']"
        return self.find(selector, SelectorType.CSS, timeout_ms)
    
    def wait_for_visible(
        self,
        selector: str,
        selector_type: SelectorType = SelectorType.CSS,
        timeout_ms: int = 10000,
    ) -> bool:
        try:
            self.find_visible(selector, selector_type, timeout_ms)
            return True
        except ElementNotFoundError:
            return False
    
    def wait_for_hidden(
        self,
        selector: str,
        selector_type: SelectorType = SelectorType.CSS,
        timeout_ms: int = 10000,
    ) -> bool:
        by = self._get_by(selector_type)
        timeout_sec = timeout_ms / 1000
        
        try:
            wait = WebDriverWait(self.driver, timeout_sec)
            wait.until(EC.invisibility_of_element_located((by, selector)))
            return True
        except Exception:
            return False
    
    def wait_for_clickable(
        self,
        selector: str,
        selector_type: SelectorType = SelectorType.CSS,
        timeout_ms: int = 10000,
    ) -> bool:
        try:
            self.find_clickable(selector, selector_type, timeout_ms)
            return True
        except ElementNotFoundError:
            return False
    
    def wait_for_text(
        self,
        selector: str,
        text: str,
        selector_type: SelectorType = SelectorType.CSS,
        timeout_ms: int = 10000,
    ) -> bool:
        by = self._get_by(selector_type)
        timeout_sec = timeout_ms / 1000
        
        try:
            wait = WebDriverWait(self.driver, timeout_sec)
            wait.until(EC.text_to_be_present_in_element((by, selector), text))
            return True
        except Exception:
            return False
    
    def wait_for_value(
        self,
        selector: str,
        value: str,
        selector_type: SelectorType = SelectorType.CSS,
        timeout_ms: int = 10000,
    ) -> bool:
        by = self._get_by(selector_type)
        timeout_sec = timeout_ms / 1000
        
        try:
            wait = WebDriverWait(self.driver, timeout_sec)
            wait.until(EC.text_to_be_present_in_element_value((by, selector), value))
            return True
        except Exception:
            return False
    
    def scroll_into_view(self, element: WebElement) -> None:
        try:
            self.driver.execute_script(
                "arguments[0].scrollIntoView({behavior: 'instant', block: 'center'});",
                element
            )
            time.sleep(0.2)
        except Exception:
            pass
    
    def scroll_to_top(self) -> None:
        self.driver.execute_script("window.scrollTo(0, 0);")
    
    def scroll_to_bottom(self) -> None:
        self.driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
    
    def is_visible(self, element: WebElement) -> bool:
        try:
            return element.is_displayed()
        except Exception:
            return False
    
    def is_enabled(self, element: WebElement) -> bool:
        try:
            return element.is_enabled()
        except Exception:
            return False
    
    def is_stale(self, element: WebElement) -> bool:
        try:
            element.is_enabled()
            return False
        except StaleElementReferenceException:
            return True
        except Exception:
            return True
    
    def get_element_info(self, element: WebElement) -> dict:
        try:
            return {
                "tag": element.tag_name,
                "id": element.get_attribute("id"),
                "name": element.get_attribute("name"),
                "type": element.get_attribute("type"),
                "value": element.get_attribute("value"),
                "text": element.text,
                "visible": element.is_displayed(),
                "enabled": element.is_enabled(),
                "selected": element.is_selected() if element.tag_name in ["input", "option"] else None,
            }
        except Exception:
            return {}
    
    def remove_overlays(self) -> None:
        js = """
        var overlays = document.querySelectorAll('[class*="overlay"], [class*="modal"], [class*="popup"]');
        overlays.forEach(function(el) {
            if (el.style.position === 'fixed' || el.style.position === 'absolute') {
                el.style.display = 'none';
            }
        });
        """
        try:
            self.driver.execute_script(js)
        except Exception:
            pass
    
    def force_click(self, element: WebElement) -> None:
        try:
            self.driver.execute_script("arguments[0].click();", element)
        except Exception:
            element.click()
