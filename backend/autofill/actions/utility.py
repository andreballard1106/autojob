import time

from selenium.webdriver.common.keys import Keys
from selenium.webdriver.common.action_chains import ActionChains
from selenium.webdriver.common.by import By

from autofill.actions.base import BaseAction
from autofill.models import FillCommand, FillResult, ActionType, WaitCondition
from autofill.exceptions import ElementNotFoundError


class ClearAction(BaseAction):
    action_type = ActionType.CLEAR
    
    def execute(self, command: FillCommand) -> FillResult:
        start = time.time()
        
        try:
            element = self.locator.find_visible(
                command.selector,
                command.selector_type,
                command.timeout_ms,
            )
            
            try:
                element.clear()
            except Exception:
                pass
            
            try:
                element.send_keys(Keys.CONTROL + "a")
                element.send_keys(Keys.DELETE)
            except Exception:
                pass
            
            try:
                self.driver.execute_script(
                    "arguments[0].value = '';",
                    element
                )
                self.driver.execute_script(
                    "arguments[0].dispatchEvent(new Event('input', { bubbles: true }));",
                    element
                )
            except Exception:
                pass
            
            self._wait_after(command)
            
            duration = int((time.time() - start) * 1000)
            return self._create_result(
                command,
                success=True,
                value_used="cleared",
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


class FocusAction(BaseAction):
    action_type = ActionType.FOCUS
    
    def execute(self, command: FillCommand) -> FillResult:
        start = time.time()
        
        try:
            element = self.locator.find(
                command.selector,
                command.selector_type,
                command.timeout_ms,
            )
            
            self.locator.scroll_into_view(element)
            
            try:
                element.click()
            except Exception:
                pass
            
            self.driver.execute_script("arguments[0].focus();", element)
            
            self._wait_after(command)
            
            duration = int((time.time() - start) * 1000)
            return self._create_result(
                command,
                success=True,
                value_used="focused",
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


class BlurAction(BaseAction):
    action_type = ActionType.BLUR
    
    def execute(self, command: FillCommand) -> FillResult:
        start = time.time()
        
        try:
            element = self.locator.find(
                command.selector,
                command.selector_type,
                command.timeout_ms,
            )
            
            self.driver.execute_script("arguments[0].blur();", element)
            self.driver.execute_script(
                "arguments[0].dispatchEvent(new Event('blur', { bubbles: true }));",
                element
            )
            
            self._wait_after(command)
            
            duration = int((time.time() - start) * 1000)
            return self._create_result(
                command,
                success=True,
                value_used="blurred",
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


class ScrollToAction(BaseAction):
    action_type = ActionType.SCROLL_TO
    
    def execute(self, command: FillCommand) -> FillResult:
        start = time.time()
        
        try:
            element = self.locator.find(
                command.selector,
                command.selector_type,
                command.timeout_ms,
            )
            
            self.locator.scroll_into_view(element)
            
            self._wait_after(command)
            
            duration = int((time.time() - start) * 1000)
            return self._create_result(
                command,
                success=True,
                value_used="scrolled",
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


class ScrollByAction(BaseAction):
    action_type = ActionType.SCROLL_BY
    
    def execute(self, command: FillCommand) -> FillResult:
        start = time.time()
        
        try:
            x = command.options.get("x", 0)
            y = command.options.get("y", 0)
            
            if command.value:
                if isinstance(command.value, dict):
                    x = command.value.get("x", 0)
                    y = command.value.get("y", 0)
                elif isinstance(command.value, (int, float)):
                    y = command.value
            
            self.driver.execute_script(f"window.scrollBy({x}, {y});")
            
            self._wait_after(command)
            
            duration = int((time.time() - start) * 1000)
            return self._create_result(
                command,
                success=True,
                value_used={"x": x, "y": y},
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


class WaitAction(BaseAction):
    action_type = ActionType.WAIT
    
    def execute(self, command: FillCommand) -> FillResult:
        start = time.time()
        
        try:
            if command.time_ms > 0:
                time.sleep(command.time_ms / 1000)
                duration = int((time.time() - start) * 1000)
                return self._create_result(
                    command,
                    success=True,
                    value_used=f"waited {command.time_ms}ms",
                    duration_ms=duration,
                )
            
            if command.selector:
                success = False
                
                if command.condition == WaitCondition.VISIBLE:
                    success = self.locator.wait_for_visible(
                        command.selector,
                        command.selector_type,
                        command.timeout_ms,
                    )
                elif command.condition == WaitCondition.HIDDEN:
                    success = self.locator.wait_for_hidden(
                        command.selector,
                        command.selector_type,
                        command.timeout_ms,
                    )
                elif command.condition == WaitCondition.CLICKABLE:
                    success = self.locator.wait_for_clickable(
                        command.selector,
                        command.selector_type,
                        command.timeout_ms,
                    )
                elif command.condition == WaitCondition.PRESENT:
                    try:
                        self.locator.find(
                            command.selector,
                            command.selector_type,
                            command.timeout_ms,
                        )
                        success = True
                    except ElementNotFoundError:
                        success = False
                
                duration = int((time.time() - start) * 1000)
                return self._create_result(
                    command,
                    success=success,
                    value_used=f"wait for {command.condition.value}",
                    error=None if success else f"Condition not met: {command.condition.value}",
                    duration_ms=duration,
                )
            
            duration = int((time.time() - start) * 1000)
            return self._create_result(
                command,
                success=True,
                value_used="no wait specified",
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


class PressKeyAction(BaseAction):
    action_type = ActionType.PRESS_KEY
    
    KEY_MAP = {
        "enter": Keys.ENTER,
        "return": Keys.RETURN,
        "tab": Keys.TAB,
        "escape": Keys.ESCAPE,
        "esc": Keys.ESCAPE,
        "backspace": Keys.BACKSPACE,
        "delete": Keys.DELETE,
        "space": Keys.SPACE,
        "up": Keys.UP,
        "down": Keys.DOWN,
        "left": Keys.LEFT,
        "right": Keys.RIGHT,
        "home": Keys.HOME,
        "end": Keys.END,
        "pageup": Keys.PAGE_UP,
        "pagedown": Keys.PAGE_DOWN,
        "f1": Keys.F1,
        "f2": Keys.F2,
        "f3": Keys.F3,
        "f4": Keys.F4,
        "f5": Keys.F5,
        "f6": Keys.F6,
        "f7": Keys.F7,
        "f8": Keys.F8,
        "f9": Keys.F9,
        "f10": Keys.F10,
        "f11": Keys.F11,
        "f12": Keys.F12,
        "ctrl": Keys.CONTROL,
        "control": Keys.CONTROL,
        "alt": Keys.ALT,
        "shift": Keys.SHIFT,
    }
    
    def execute(self, command: FillCommand) -> FillResult:
        start = time.time()
        
        try:
            key = command.key or command.value
            
            if not key:
                duration = int((time.time() - start) * 1000)
                return self._create_result(
                    command,
                    success=False,
                    error="No key specified",
                    duration_ms=duration,
                )
            
            key_str = str(key).lower()
            
            if "+" in key_str:
                keys = key_str.split("+")
                actions = ActionChains(self.driver)
                
                for k in keys[:-1]:
                    modifier = self.KEY_MAP.get(k.strip())
                    if modifier:
                        actions.key_down(modifier)
                
                final_key = self.KEY_MAP.get(keys[-1].strip(), keys[-1])
                actions.send_keys(final_key)
                
                for k in reversed(keys[:-1]):
                    modifier = self.KEY_MAP.get(k.strip())
                    if modifier:
                        actions.key_up(modifier)
                
                actions.perform()
            else:
                selenium_key = self.KEY_MAP.get(key_str, key)
                
                if command.selector:
                    element = self.locator.find_visible(
                        command.selector,
                        command.selector_type,
                        command.timeout_ms,
                    )
                    element.send_keys(selenium_key)
                else:
                    actions = ActionChains(self.driver)
                    actions.send_keys(selenium_key).perform()
            
            self._wait_after(command)
            
            duration = int((time.time() - start) * 1000)
            return self._create_result(
                command,
                success=True,
                value_used=key,
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


class HoverAction(BaseAction):
    action_type = ActionType.HOVER
    
    def execute(self, command: FillCommand) -> FillResult:
        start = time.time()
        
        try:
            element = self.locator.find_visible(
                command.selector,
                command.selector_type,
                command.timeout_ms,
            )
            
            self.locator.scroll_into_view(element)
            
            actions = ActionChains(self.driver)
            actions.move_to_element(element).perform()
            
            self._wait_after(command)
            
            duration = int((time.time() - start) * 1000)
            return self._create_result(
                command,
                success=True,
                value_used="hovered",
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


class SetValueAction(BaseAction):
    action_type = ActionType.SET_VALUE
    
    def execute(self, command: FillCommand) -> FillResult:
        start = time.time()
        
        try:
            element = self.locator.find(
                command.selector,
                command.selector_type,
                command.timeout_ms,
            )
            
            value = str(command.value) if command.value is not None else ""
            
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


class ExecuteJsAction(BaseAction):
    action_type = ActionType.EXECUTE_JS
    
    def execute(self, command: FillCommand) -> FillResult:
        start = time.time()
        
        try:
            js_code = command.value or command.options.get("script", "")
            
            if not js_code:
                duration = int((time.time() - start) * 1000)
                return self._create_result(
                    command,
                    success=False,
                    error="No JavaScript code provided",
                    duration_ms=duration,
                )
            
            if command.selector:
                element = self.locator.find(
                    command.selector,
                    command.selector_type,
                    command.timeout_ms,
                )
                result = self.driver.execute_script(js_code, element)
            else:
                result = self.driver.execute_script(js_code)
            
            self._wait_after(command)
            
            duration = int((time.time() - start) * 1000)
            return self._create_result(
                command,
                success=True,
                value_used=result,
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


class SwitchIframeAction(BaseAction):
    action_type = ActionType.SWITCH_IFRAME
    
    def execute(self, command: FillCommand) -> FillResult:
        start = time.time()
        
        try:
            element = self.locator.find(
                command.selector,
                command.selector_type,
                command.timeout_ms,
            )
            
            self.driver.switch_to.frame(element)
            
            self._wait_after(command)
            
            duration = int((time.time() - start) * 1000)
            return self._create_result(
                command,
                success=True,
                value_used="switched to iframe",
                duration_ms=duration,
            )
            
        except ElementNotFoundError:
            duration = int((time.time() - start) * 1000)
            return self._create_result(
                command,
                success=False,
                element_found=False,
                error=f"Iframe not found: {command.selector}",
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


class SwitchDefaultAction(BaseAction):
    action_type = ActionType.SWITCH_DEFAULT
    
    def execute(self, command: FillCommand) -> FillResult:
        start = time.time()
        
        try:
            self.driver.switch_to.default_content()
            
            self._wait_after(command)
            
            duration = int((time.time() - start) * 1000)
            return self._create_result(
                command,
                success=True,
                value_used="switched to default content",
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


class DragDropAction(BaseAction):
    action_type = ActionType.DRAG_DROP
    
    def execute(self, command: FillCommand) -> FillResult:
        start = time.time()
        
        try:
            source = self.locator.find_visible(
                command.selector,
                command.selector_type,
                command.timeout_ms,
            )
            
            target_selector = command.options.get("target") or command.value
            if not target_selector:
                duration = int((time.time() - start) * 1000)
                return self._create_result(
                    command,
                    success=False,
                    error="No target selector provided",
                    duration_ms=duration,
                )
            
            target = self.locator.find_visible(
                target_selector,
                command.selector_type,
                command.timeout_ms,
            )
            
            actions = ActionChains(self.driver)
            actions.drag_and_drop(source, target).perform()
            
            self._wait_after(command)
            
            duration = int((time.time() - start) * 1000)
            return self._create_result(
                command,
                success=True,
                value_used=f"dragged to {target_selector}",
                duration_ms=duration,
            )
            
        except ElementNotFoundError as e:
            duration = int((time.time() - start) * 1000)
            return self._create_result(
                command,
                success=False,
                element_found=False,
                error=str(e),
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
