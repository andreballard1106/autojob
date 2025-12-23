import time
from typing import Any

from selenium.webdriver.common.keys import Keys
from selenium.webdriver.common.action_chains import ActionChains

from autofill.actions.base import BaseAction
from autofill.models import FillCommand, FillResult, ActionType
from autofill.exceptions import ElementNotFoundError


class TypeTextAction(BaseAction):
    action_type = ActionType.TYPE_TEXT
    
    def execute(self, command: FillCommand) -> FillResult:
        start = time.time()
        
        try:
            element = self.locator.find_visible(
                command.selector,
                command.selector_type,
                command.timeout_ms,
            )
            
            self.locator.scroll_into_view(element)
            
            tag_name = element.tag_name.lower()
            is_contenteditable = element.get_attribute("contenteditable") == "true"
            input_type = element.get_attribute("type") or "text"
            
            value = str(command.value) if command.value is not None else ""
            
            if is_contenteditable:
                success = self._fill_contenteditable(element, value, command)
            elif tag_name in ["input", "textarea"]:
                success = self._fill_input(element, value, command, input_type)
            else:
                success = self._fill_generic(element, value, command)
            
            if not success:
                raise Exception("Failed to set value")
            
            self._trigger_events(element)
            self._wait_after(command)
            
            duration = int((time.time() - start) * 1000)
            return self._create_result(
                command,
                success=True,
                value_used=value,
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
    
    def _fill_input(self, element, value: str, command: FillCommand, input_type: str) -> bool:
        try:
            element.click()
            time.sleep(0.1)
        except Exception:
            pass
        
        if command.clear_first:
            self._clear_input(element)
        
        if command.delay_ms > 0:
            for char in value:
                element.send_keys(char)
                time.sleep(command.delay_ms / 1000)
        else:
            element.send_keys(value)
        
        if command.options.get("use_js_fallback", True):
            actual_value = element.get_attribute("value") or ""
            if actual_value != value:
                self._set_value_via_js(element, value)
        
        return True
    
    def _fill_contenteditable(self, element, value: str, command: FillCommand) -> bool:
        try:
            element.click()
            time.sleep(0.1)
        except Exception:
            pass
        
        if command.clear_first:
            self.driver.execute_script("arguments[0].innerHTML = '';", element)
        
        if command.delay_ms > 0:
            for char in value:
                element.send_keys(char)
                time.sleep(command.delay_ms / 1000)
        else:
            self.driver.execute_script(
                "arguments[0].innerHTML = arguments[1];",
                element,
                value
            )
        
        return True
    
    def _fill_generic(self, element, value: str, command: FillCommand) -> bool:
        try:
            element.click()
            time.sleep(0.1)
            element.send_keys(value)
            return True
        except Exception:
            return False
    
    def _clear_input(self, element) -> None:
        try:
            element.clear()
        except Exception:
            pass
        
        try:
            element.send_keys(Keys.CONTROL + "a")
            element.send_keys(Keys.BACKSPACE)
        except Exception:
            pass
        
        try:
            current = element.get_attribute("value") or ""
            if current:
                for _ in range(len(current)):
                    element.send_keys(Keys.BACKSPACE)
        except Exception:
            pass
    
    def _set_value_via_js(self, element, value: str) -> None:
        js = """
        var el = arguments[0];
        var value = arguments[1];
        
        var nativeInputValueSetter = Object.getOwnPropertyDescriptor(
            window.HTMLInputElement.prototype, 'value'
        )?.set || Object.getOwnPropertyDescriptor(
            window.HTMLTextAreaElement.prototype, 'value'
        )?.set;
        
        if (nativeInputValueSetter) {
            nativeInputValueSetter.call(el, value);
        } else {
            el.value = value;
        }
        
        el.dispatchEvent(new Event('input', { bubbles: true }));
        el.dispatchEvent(new Event('change', { bubbles: true }));
        """
        self.driver.execute_script(js, element, value)
    
    def _trigger_events(self, element) -> None:
        js = """
        var el = arguments[0];
        el.dispatchEvent(new Event('input', { bubbles: true }));
        el.dispatchEvent(new Event('change', { bubbles: true }));
        el.dispatchEvent(new Event('blur', { bubbles: true }));
        """
        try:
            self.driver.execute_script(js, element)
        except Exception:
            pass


class TypeNumberAction(BaseAction):
    action_type = ActionType.TYPE_NUMBER
    
    def execute(self, command: FillCommand) -> FillResult:
        start = time.time()
        
        try:
            element = self.locator.find_visible(
                command.selector,
                command.selector_type,
                command.timeout_ms,
            )
            
            self.locator.scroll_into_view(element)
            
            input_type = element.get_attribute("type") or "text"
            value = command.value
            
            if value is not None:
                value_str = str(value)
            else:
                value_str = ""
            
            try:
                element.click()
                time.sleep(0.1)
            except Exception:
                pass
            
            if command.clear_first:
                self._clear_input(element)
            
            if input_type == "range":
                self._set_range_value(element, value)
            else:
                element.send_keys(value_str)
                
                actual_value = element.get_attribute("value") or ""
                if actual_value != value_str:
                    self._set_value_via_js(element, value_str)
            
            self._trigger_events(element)
            self._wait_after(command)
            
            duration = int((time.time() - start) * 1000)
            return self._create_result(
                command,
                success=True,
                value_used=value_str,
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
    
    def _clear_input(self, element) -> None:
        try:
            element.clear()
        except Exception:
            pass
        
        try:
            element.send_keys(Keys.CONTROL + "a")
            element.send_keys(Keys.BACKSPACE)
        except Exception:
            pass
    
    def _set_range_value(self, element, value) -> None:
        js = """
        var el = arguments[0];
        var value = arguments[1];
        el.value = value;
        el.dispatchEvent(new Event('input', { bubbles: true }));
        el.dispatchEvent(new Event('change', { bubbles: true }));
        """
        self.driver.execute_script(js, element, value)
    
    def _set_value_via_js(self, element, value: str) -> None:
        js = """
        var el = arguments[0];
        var value = arguments[1];
        
        var nativeInputValueSetter = Object.getOwnPropertyDescriptor(
            window.HTMLInputElement.prototype, 'value'
        )?.set;
        
        if (nativeInputValueSetter) {
            nativeInputValueSetter.call(el, value);
        } else {
            el.value = value;
        }
        
        el.dispatchEvent(new Event('input', { bubbles: true }));
        el.dispatchEvent(new Event('change', { bubbles: true }));
        """
        self.driver.execute_script(js, element, value)
    
    def _trigger_events(self, element) -> None:
        js = """
        var el = arguments[0];
        el.dispatchEvent(new Event('input', { bubbles: true }));
        el.dispatchEvent(new Event('change', { bubbles: true }));
        el.dispatchEvent(new Event('blur', { bubbles: true }));
        """
        try:
            self.driver.execute_script(js, element)
        except Exception:
            pass
