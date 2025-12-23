import time
from datetime import datetime, date

from selenium.webdriver.common.keys import Keys

from autofill.actions.base import BaseAction
from autofill.models import FillCommand, FillResult, ActionType
from autofill.exceptions import ElementNotFoundError


class EnterDateAction(BaseAction):
    action_type = ActionType.ENTER_DATE
    
    def execute(self, command: FillCommand) -> FillResult:
        start = time.time()
        
        try:
            element = self.locator.find_visible(
                command.selector,
                command.selector_type,
                command.timeout_ms,
            )
            
            self.locator.scroll_into_view(element)
            
            formatted_date = self._format_date(command.value, command.date_format)
            
            if command.clear_first:
                element.clear()
                element.send_keys(Keys.CONTROL + "a")
                element.send_keys(Keys.DELETE)
            
            input_type = element.get_attribute("type")
            
            if input_type == "date":
                self.driver.execute_script(
                    "arguments[0].value = arguments[1];",
                    element,
                    self._to_iso_date(command.value),
                )
                self.driver.execute_script(
                    "arguments[0].dispatchEvent(new Event('change', { bubbles: true }));",
                    element,
                )
            else:
                element.send_keys(formatted_date)
            
            self._wait_after(command)
            
            duration = int((time.time() - start) * 1000)
            return self._create_result(
                command,
                success=True,
                value_used=formatted_date,
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
    
    def _format_date(self, value, format_str: str) -> str:
        if isinstance(value, str):
            try:
                for fmt in ["%Y-%m-%d", "%m/%d/%Y", "%d/%m/%Y", "%Y/%m/%d"]:
                    try:
                        dt = datetime.strptime(value, fmt)
                        break
                    except ValueError:
                        continue
                else:
                    return value
            except Exception:
                return str(value)
        elif isinstance(value, (datetime, date)):
            dt = value
        else:
            return str(value)
        
        format_map = {
            "YYYY": "%Y",
            "YY": "%y",
            "MM": "%m",
            "DD": "%d",
            "M": "%-m",
            "D": "%-d",
        }
        
        py_format = format_str
        for key, val in format_map.items():
            py_format = py_format.replace(key, val)
        
        try:
            return dt.strftime(py_format)
        except Exception:
            return dt.strftime("%Y-%m-%d")
    
    def _to_iso_date(self, value) -> str:
        if isinstance(value, str):
            for fmt in ["%Y-%m-%d", "%m/%d/%Y", "%d/%m/%Y", "%Y/%m/%d"]:
                try:
                    dt = datetime.strptime(value, fmt)
                    return dt.strftime("%Y-%m-%d")
                except ValueError:
                    continue
            return value
        elif isinstance(value, (datetime, date)):
            return value.strftime("%Y-%m-%d")
        return str(value)

