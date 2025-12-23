import time
import logging
from typing import Dict, Any, List, Union

from selenium.webdriver.remote.webdriver import WebDriver

from autofill.models import FillCommand, FillResult, ActionType
from autofill.actions.registry import ActionRegistry
from autofill.exceptions import InvalidCommandError, AutofillError

logger = logging.getLogger(__name__)


class AutofillEngine:
    def __init__(self, driver: WebDriver):
        self.driver = driver
        self.registry = ActionRegistry(driver)
        self._stop_on_error = False
        self._retry_count = 0
        self._retry_delay_ms = 500
    
    def configure(
        self,
        stop_on_error: bool = False,
        retry_count: int = 0,
        retry_delay_ms: int = 500,
    ) -> "AutofillEngine":
        self._stop_on_error = stop_on_error
        self._retry_count = retry_count
        self._retry_delay_ms = retry_delay_ms
        return self
    
    def execute(self, command: Union[Dict[str, Any], FillCommand]) -> FillResult:
        if isinstance(command, dict):
            try:
                command = FillCommand.from_dict(command)
            except Exception as e:
                return FillResult(
                    success=False,
                    action=command.get("action", "unknown"),
                    selector=command.get("selector"),
                    error=f"Invalid command: {e}",
                )
        
        action_handler = self.registry.get_action(command.action)
        
        last_result = None
        attempts = self._retry_count + 1
        
        for attempt in range(attempts):
            result = action_handler.execute(command)
            last_result = result
            
            if result.success:
                return result
            
            if attempt < attempts - 1:
                time.sleep(self._retry_delay_ms / 1000)
        
        return last_result
    
    def execute_all(
        self,
        commands: List[Union[Dict[str, Any], FillCommand]],
    ) -> List[FillResult]:
        results = []
        
        for command in commands:
            result = self.execute(command)
            results.append(result)
            
            if not result.success and self._stop_on_error:
                break
        
        return results
    
    def type_text(
        self,
        selector: str,
        value: str,
        clear_first: bool = True,
        delay_ms: int = 0,
        selector_type: str = "css",
    ) -> FillResult:
        return self.execute({
            "action": "type_text",
            "selector": selector,
            "selector_type": selector_type,
            "value": value,
            "clear_first": clear_first,
            "delay_ms": delay_ms,
        })
    
    def type_number(
        self,
        selector: str,
        value: Union[int, float],
        clear_first: bool = True,
        selector_type: str = "css",
    ) -> FillResult:
        return self.execute({
            "action": "type_number",
            "selector": selector,
            "selector_type": selector_type,
            "value": value,
            "clear_first": clear_first,
        })
    
    def select_option(
        self,
        selector: str,
        value: str,
        select_by: str = "value",
        selector_type: str = "css",
    ) -> FillResult:
        return self.execute({
            "action": "select_option",
            "selector": selector,
            "selector_type": selector_type,
            "value": value,
            "select_by": select_by,
        })
    
    def select_multiple(
        self,
        selector: str,
        values: List[str],
        select_by: str = "value",
        selector_type: str = "css",
    ) -> FillResult:
        return self.execute({
            "action": "select_multiple",
            "selector": selector,
            "selector_type": selector_type,
            "value": values,
            "select_by": select_by,
        })
    
    def check(
        self,
        selector: str,
        checked: bool = True,
        selector_type: str = "css",
    ) -> FillResult:
        return self.execute({
            "action": "check",
            "selector": selector,
            "selector_type": selector_type,
            "checked": checked,
        })
    
    def select_radio(
        self,
        selector: str = None,
        name: str = None,
        value: str = None,
        selector_type: str = "css",
    ) -> FillResult:
        return self.execute({
            "action": "select_radio",
            "selector": selector,
            "selector_type": selector_type,
            "name": name,
            "value": value,
        })
    
    def upload_file(
        self,
        selector: str,
        file_path: str = None,
        file_paths: List[str] = None,
        selector_type: str = "css",
    ) -> FillResult:
        return self.execute({
            "action": "upload_file",
            "selector": selector,
            "selector_type": selector_type,
            "file_path": file_path,
            "file_paths": file_paths,
        })
    
    def enter_date(
        self,
        selector: str,
        value: str,
        date_format: str = "YYYY-MM-DD",
        clear_first: bool = True,
        selector_type: str = "css",
    ) -> FillResult:
        return self.execute({
            "action": "enter_date",
            "selector": selector,
            "selector_type": selector_type,
            "value": value,
            "date_format": date_format,
            "clear_first": clear_first,
        })
    
    def click(
        self,
        selector: str,
        double_click: bool = False,
        wait_after_ms: int = 0,
        selector_type: str = "css",
    ) -> FillResult:
        return self.execute({
            "action": "click",
            "selector": selector,
            "selector_type": selector_type,
            "double_click": double_click,
            "wait_after_ms": wait_after_ms,
        })
    
    def clear(
        self,
        selector: str,
        selector_type: str = "css",
    ) -> FillResult:
        return self.execute({
            "action": "clear",
            "selector": selector,
            "selector_type": selector_type,
        })
    
    def focus(
        self,
        selector: str,
        selector_type: str = "css",
    ) -> FillResult:
        return self.execute({
            "action": "focus",
            "selector": selector,
            "selector_type": selector_type,
        })
    
    def scroll_to(
        self,
        selector: str,
        selector_type: str = "css",
    ) -> FillResult:
        return self.execute({
            "action": "scroll_to",
            "selector": selector,
            "selector_type": selector_type,
        })
    
    def wait(
        self,
        time_ms: int = 0,
        selector: str = None,
        condition: str = "visible",
        timeout_ms: int = 10000,
        selector_type: str = "css",
    ) -> FillResult:
        return self.execute({
            "action": "wait",
            "time_ms": time_ms,
            "selector": selector,
            "selector_type": selector_type,
            "condition": condition,
            "timeout_ms": timeout_ms,
        })
    
    def press_key(
        self,
        key: str,
        selector: str = None,
        selector_type: str = "css",
    ) -> FillResult:
        return self.execute({
            "action": "press_key",
            "key": key,
            "selector": selector,
            "selector_type": selector_type,
        })
    
    def hover(
        self,
        selector: str,
        selector_type: str = "css",
        wait_after_ms: int = 0,
    ) -> FillResult:
        return self.execute({
            "action": "hover",
            "selector": selector,
            "selector_type": selector_type,
            "wait_after_ms": wait_after_ms,
        })
    
    def double_click(
        self,
        selector: str,
        selector_type: str = "css",
        wait_after_ms: int = 0,
    ) -> FillResult:
        return self.execute({
            "action": "double_click",
            "selector": selector,
            "selector_type": selector_type,
            "wait_after_ms": wait_after_ms,
        })
    
    def right_click(
        self,
        selector: str,
        selector_type: str = "css",
        wait_after_ms: int = 0,
    ) -> FillResult:
        return self.execute({
            "action": "right_click",
            "selector": selector,
            "selector_type": selector_type,
            "wait_after_ms": wait_after_ms,
        })
    
    def blur(
        self,
        selector: str,
        selector_type: str = "css",
    ) -> FillResult:
        return self.execute({
            "action": "blur",
            "selector": selector,
            "selector_type": selector_type,
        })
    
    def set_value(
        self,
        selector: str,
        value: str,
        selector_type: str = "css",
    ) -> FillResult:
        return self.execute({
            "action": "set_value",
            "selector": selector,
            "selector_type": selector_type,
            "value": value,
        })
    
    def execute_js(
        self,
        script: str,
        selector: str = None,
        selector_type: str = "css",
    ) -> FillResult:
        return self.execute({
            "action": "execute_js",
            "selector": selector,
            "selector_type": selector_type,
            "value": script,
        })
    
    def switch_iframe(
        self,
        selector: str,
        selector_type: str = "css",
    ) -> FillResult:
        return self.execute({
            "action": "switch_iframe",
            "selector": selector,
            "selector_type": selector_type,
        })
    
    def switch_default(self) -> FillResult:
        return self.execute({
            "action": "switch_default",
        })
    
    def drag_drop(
        self,
        source_selector: str,
        target_selector: str,
        selector_type: str = "css",
    ) -> FillResult:
        return self.execute({
            "action": "drag_drop",
            "selector": source_selector,
            "selector_type": selector_type,
            "options": {"target": target_selector},
        })
    
    def select_autocomplete(
        self,
        selector: str,
        value: str,
        selector_type: str = "css",
    ) -> FillResult:
        return self.execute({
            "action": "select_autocomplete",
            "selector": selector,
            "selector_type": selector_type,
            "value": value,
        })
    
    def fill_form(self, fields: Dict[str, Any]) -> Dict[str, FillResult]:
        results = {}
        for selector, value in fields.items():
            if isinstance(value, dict):
                command = {"selector": selector, **value}
                if "action" not in command:
                    command["action"] = "type_text"
            else:
                command = {
                    "action": "type_text",
                    "selector": selector,
                    "value": value,
                }
            results[selector] = self.execute(command)
        return results
    
    def get_results_summary(self, results: List[FillResult]) -> Dict[str, Any]:
        successful = sum(1 for r in results if r.success)
        failed = sum(1 for r in results if not r.success)
        total_duration = sum(r.duration_ms for r in results)
        
        return {
            "total": len(results),
            "successful": successful,
            "failed": failed,
            "success_rate": successful / len(results) if results else 0,
            "total_duration_ms": total_duration,
            "failures": [
                {"selector": r.selector, "action": r.action.value, "error": r.error}
                for r in results if not r.success
            ],
        }

