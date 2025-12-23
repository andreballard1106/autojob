import time

from selenium.webdriver.common.action_chains import ActionChains

from autofill.actions.base import BaseAction
from autofill.models import FillCommand, FillResult, ActionType
from autofill.exceptions import ElementNotFoundError


class ClickAction(BaseAction):
    action_type = ActionType.CLICK
    
    def execute(self, command: FillCommand) -> FillResult:
        start = time.time()
        
        try:
            element = self.locator.find_clickable(
                command.selector,
                command.selector_type,
                command.timeout_ms,
            )
            
            self.locator.scroll_into_view(element)
            
            try:
                element.click()
            except Exception:
                self.driver.execute_script("arguments[0].click();", element)
            
            self._wait_after(command)
            
            duration = int((time.time() - start) * 1000)
            return self._create_result(
                command,
                success=True,
                value_used="click",
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


class DoubleClickAction(BaseAction):
    action_type = ActionType.DOUBLE_CLICK
    
    def execute(self, command: FillCommand) -> FillResult:
        start = time.time()
        
        try:
            element = self.locator.find_clickable(
                command.selector,
                command.selector_type,
                command.timeout_ms,
            )
            
            self.locator.scroll_into_view(element)
            
            actions = ActionChains(self.driver)
            actions.double_click(element).perform()
            
            self._wait_after(command)
            
            duration = int((time.time() - start) * 1000)
            return self._create_result(
                command,
                success=True,
                value_used="double_click",
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


class RightClickAction(BaseAction):
    action_type = ActionType.RIGHT_CLICK
    
    def execute(self, command: FillCommand) -> FillResult:
        start = time.time()
        
        try:
            element = self.locator.find_clickable(
                command.selector,
                command.selector_type,
                command.timeout_ms,
            )
            
            self.locator.scroll_into_view(element)
            
            actions = ActionChains(self.driver)
            actions.context_click(element).perform()
            
            self._wait_after(command)
            
            duration = int((time.time() - start) * 1000)
            return self._create_result(
                command,
                success=True,
                value_used="right_click",
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
