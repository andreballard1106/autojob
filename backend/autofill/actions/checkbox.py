import time

from selenium.webdriver.common.by import By

from autofill.actions.base import BaseAction
from autofill.models import FillCommand, FillResult, ActionType, SelectorType
from autofill.exceptions import ElementNotFoundError


class CheckAction(BaseAction):
    action_type = ActionType.CHECK
    
    def execute(self, command: FillCommand) -> FillResult:
        start = time.time()
        
        try:
            element = self.locator.find(
                command.selector,
                command.selector_type,
                command.timeout_ms,
            )
            
            self.locator.scroll_into_view(element)
            
            tag_name = element.tag_name.lower()
            input_type = (element.get_attribute("type") or "").lower()
            role = (element.get_attribute("role") or "").lower()
            
            should_check = command.checked
            
            if tag_name == "input" and input_type == "checkbox":
                success = self._handle_native_checkbox(element, should_check)
            elif role in ["checkbox", "switch"]:
                success = self._handle_aria_checkbox(element, should_check)
            else:
                success = self._handle_custom_checkbox(element, should_check, command)
            
            if not success:
                raise Exception("Failed to set checkbox state")
            
            self._wait_after(command)
            
            duration = int((time.time() - start) * 1000)
            return self._create_result(
                command,
                success=True,
                value_used=should_check,
                duration_ms=duration,
            )
            
        except ElementNotFoundError:
            duration = int((time.time() - start) * 1000)
            return self._create_result(
                command,
                success=False,
                element_found=False,
                error=f"Element not found: {command.selector}",
                duration_ms=duration,
            )
        except Exception as e:
            duration = int((time.time() - start) * 1000)
            return self._create_result(
                command,
                success=False,
                error=str(e),
                duration_ms=duration,
            )
    
    def _handle_native_checkbox(self, element, should_check: bool) -> bool:
        try:
            is_checked = element.is_selected()
            
            if is_checked != should_check:
                try:
                    element.click()
                except Exception:
                    self.driver.execute_script("arguments[0].click();", element)
                
                new_state = element.is_selected()
                if new_state != should_check:
                    self.driver.execute_script(
                        "arguments[0].checked = arguments[1];",
                        element,
                        should_check
                    )
                    self.driver.execute_script(
                        "arguments[0].dispatchEvent(new Event('change', { bubbles: true }));",
                        element
                    )
            
            return True
        except Exception:
            return False
    
    def _handle_aria_checkbox(self, element, should_check: bool) -> bool:
        try:
            aria_checked = element.get_attribute("aria-checked")
            is_checked = aria_checked == "true"
            
            if is_checked != should_check:
                try:
                    element.click()
                except Exception:
                    self.driver.execute_script("arguments[0].click();", element)
            
            return True
        except Exception:
            return False
    
    def _handle_custom_checkbox(self, element, should_check: bool, command: FillCommand) -> bool:
        try:
            hidden_input = element.find_element(By.CSS_SELECTOR, "input[type='checkbox']")
            if hidden_input:
                is_checked = hidden_input.is_selected()
                if is_checked != should_check:
                    try:
                        element.click()
                    except Exception:
                        self.driver.execute_script("arguments[0].click();", element)
                return True
        except Exception:
            pass
        
        try:
            classes = element.get_attribute("class") or ""
            is_checked = any(c in classes.lower() for c in ["checked", "selected", "active", "on"])
            
            if is_checked != should_check:
                try:
                    element.click()
                except Exception:
                    self.driver.execute_script("arguments[0].click();", element)
            
            return True
        except Exception:
            pass
        
        try:
            element.click()
            return True
        except Exception:
            self.driver.execute_script("arguments[0].click();", element)
            return True


class SelectRadioAction(BaseAction):
    action_type = ActionType.SELECT_RADIO
    
    def execute(self, command: FillCommand) -> FillResult:
        start = time.time()
        
        try:
            element = None
            
            if command.name and command.value is not None:
                selectors = [
                    f"input[type='radio'][name='{command.name}'][value='{command.value}']",
                    f"[role='radio'][data-value='{command.value}']",
                    f"label:has(input[type='radio'][name='{command.name}'][value='{command.value}'])",
                ]
                
                for selector in selectors:
                    try:
                        element = self.locator.find(
                            selector,
                            SelectorType.CSS,
                            command.timeout_ms // len(selectors),
                            raise_on_not_found=False,
                        )
                        if element:
                            break
                    except Exception:
                        continue
                
                if not element:
                    radios = self.driver.find_elements(
                        By.CSS_SELECTOR,
                        f"input[type='radio'][name='{command.name}']"
                    )
                    for radio in radios:
                        try:
                            label = self.driver.find_element(
                                By.CSS_SELECTOR,
                                f"label[for='{radio.get_attribute('id')}']"
                            )
                            if str(command.value).lower() in label.text.lower():
                                element = radio
                                break
                        except Exception:
                            continue
            
            if not element and command.selector:
                element = self.locator.find(
                    command.selector,
                    command.selector_type,
                    command.timeout_ms,
                )
            
            if not element:
                raise ElementNotFoundError(
                    f"radio:{command.name}={command.value}",
                    "radio"
                )
            
            self.locator.scroll_into_view(element)
            
            tag_name = element.tag_name.lower()
            input_type = (element.get_attribute("type") or "").lower()
            role = (element.get_attribute("role") or "").lower()
            
            if tag_name == "input" and input_type == "radio":
                success = self._handle_native_radio(element)
            elif role == "radio":
                success = self._handle_aria_radio(element)
            else:
                success = self._handle_custom_radio(element)
            
            if not success:
                raise Exception("Failed to select radio option")
            
            self._wait_after(command)
            
            duration = int((time.time() - start) * 1000)
            return self._create_result(
                command,
                success=True,
                value_used=command.value or True,
                duration_ms=duration,
            )
            
        except ElementNotFoundError:
            duration = int((time.time() - start) * 1000)
            return self._create_result(
                command,
                success=False,
                element_found=False,
                error=f"Radio button not found",
                duration_ms=duration,
            )
        except Exception as e:
            duration = int((time.time() - start) * 1000)
            return self._create_result(
                command,
                success=False,
                error=str(e),
                duration_ms=duration,
            )
    
    def _handle_native_radio(self, element) -> bool:
        try:
            if not element.is_selected():
                try:
                    element.click()
                except Exception:
                    self.driver.execute_script("arguments[0].click();", element)
                
                if not element.is_selected():
                    self.driver.execute_script(
                        "arguments[0].checked = true;",
                        element
                    )
                    self.driver.execute_script(
                        "arguments[0].dispatchEvent(new Event('change', { bubbles: true }));",
                        element
                    )
            
            return True
        except Exception:
            return False
    
    def _handle_aria_radio(self, element) -> bool:
        try:
            aria_checked = element.get_attribute("aria-checked")
            if aria_checked != "true":
                try:
                    element.click()
                except Exception:
                    self.driver.execute_script("arguments[0].click();", element)
            
            return True
        except Exception:
            return False
    
    def _handle_custom_radio(self, element) -> bool:
        try:
            hidden_input = element.find_element(By.CSS_SELECTOR, "input[type='radio']")
            if hidden_input and not hidden_input.is_selected():
                try:
                    element.click()
                except Exception:
                    self.driver.execute_script("arguments[0].click();", element)
            return True
        except Exception:
            pass
        
        try:
            element.click()
            return True
        except Exception:
            self.driver.execute_script("arguments[0].click();", element)
            return True
