import time
from typing import List, Optional

from selenium.webdriver.support.ui import Select
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.common.by import By

from autofill.actions.base import BaseAction
from autofill.models import FillCommand, FillResult, ActionType, SelectBy, SelectorType
from autofill.exceptions import ElementNotFoundError


class SelectOptionAction(BaseAction):
    action_type = ActionType.SELECT_OPTION
    
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
            value = command.value
            
            if tag_name == "select":
                success = self._select_native(element, value, command)
            else:
                success = self._select_custom(element, value, command)
            
            if not success:
                raise Exception(f"Failed to select option: {value}")
            
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
    
    def _select_native(self, element, value, command: FillCommand) -> bool:
        try:
            select = Select(element)
            
            if command.select_by == SelectBy.VALUE:
                try:
                    select.select_by_value(str(value))
                    return True
                except Exception:
                    pass
                
                for option in select.options:
                    if value.lower() in (option.get_attribute("value") or "").lower():
                        select.select_by_value(option.get_attribute("value"))
                        return True
                    if value.lower() in (option.text or "").lower():
                        select.select_by_visible_text(option.text)
                        return True
                        
            elif command.select_by == SelectBy.TEXT:
                try:
                    select.select_by_visible_text(str(value))
                    return True
                except Exception:
                    pass
                
                for option in select.options:
                    if value.lower() in (option.text or "").lower():
                        select.select_by_visible_text(option.text)
                        return True
                        
            elif command.select_by == SelectBy.INDEX:
                select.select_by_index(int(value))
                return True
            
            return False
            
        except Exception:
            return False
    
    def _select_custom(self, element, value, command: FillCommand) -> bool:
        try:
            element.click()
            time.sleep(0.3)
        except Exception:
            self.driver.execute_script("arguments[0].click();", element)
            time.sleep(0.3)
        
        option_selectors = [
            f"[role='option'][data-value='{value}']",
            f"[role='option']:contains('{value}')",
            f"[role='listbox'] [data-value='{value}']",
            f".dropdown-option[data-value='{value}']",
            f".option[data-value='{value}']",
            f"li[data-value='{value}']",
        ]
        
        for selector in option_selectors:
            try:
                options = self.driver.find_elements(By.CSS_SELECTOR, selector)
                if options:
                    options[0].click()
                    return True
            except Exception:
                continue
        
        try:
            js = f"""
            var options = document.querySelectorAll('[role="option"], [role="listbox"] li, .dropdown-option, .select-option');
            for (var i = 0; i < options.length; i++) {{
                var text = options[i].textContent.trim().toLowerCase();
                var val = options[i].getAttribute('data-value') || '';
                if (text.includes('{str(value).lower()}') || val.toLowerCase().includes('{str(value).lower()}')) {{
                    options[i].click();
                    return true;
                }}
            }}
            return false;
            """
            result = self.driver.execute_script(js)
            if result:
                return True
        except Exception:
            pass
        
        try:
            input_el = element.find_element(By.CSS_SELECTOR, "input")
            if input_el:
                input_el.clear()
                input_el.send_keys(str(value))
                time.sleep(0.5)
                input_el.send_keys(Keys.ENTER)
                return True
        except Exception:
            pass
        
        try:
            element.send_keys(str(value))
            time.sleep(0.3)
            element.send_keys(Keys.ENTER)
            return True
        except Exception:
            pass
        
        return False


class SelectMultipleAction(BaseAction):
    action_type = ActionType.SELECT_MULTIPLE
    
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
            values = command.value if isinstance(command.value, list) else [command.value]
            
            if tag_name == "select":
                success = self._select_native_multiple(element, values, command)
            else:
                success = self._select_custom_multiple(element, values, command)
            
            if not success:
                raise Exception(f"Failed to select options: {values}")
            
            self._wait_after(command)
            
            duration = int((time.time() - start) * 1000)
            return self._create_result(
                command,
                success=True,
                value_used=values,
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
    
    def _select_native_multiple(self, element, values: List, command: FillCommand) -> bool:
        try:
            select = Select(element)
            
            try:
                select.deselect_all()
            except Exception:
                pass
            
            selected_count = 0
            for val in values:
                try:
                    if command.select_by == SelectBy.VALUE:
                        select.select_by_value(str(val))
                    elif command.select_by == SelectBy.TEXT:
                        select.select_by_visible_text(str(val))
                    elif command.select_by == SelectBy.INDEX:
                        select.select_by_index(int(val))
                    selected_count += 1
                except Exception:
                    for option in select.options:
                        opt_val = (option.get_attribute("value") or "").lower()
                        opt_text = (option.text or "").lower()
                        search_val = str(val).lower()
                        
                        if search_val in opt_val or search_val in opt_text:
                            try:
                                select.select_by_value(option.get_attribute("value"))
                                selected_count += 1
                                break
                            except Exception:
                                continue
            
            return selected_count > 0
            
        except Exception:
            return False
    
    def _select_custom_multiple(self, element, values: List, command: FillCommand) -> bool:
        try:
            element.click()
            time.sleep(0.3)
        except Exception:
            self.driver.execute_script("arguments[0].click();", element)
            time.sleep(0.3)
        
        selected_count = 0
        
        for val in values:
            try:
                js = f"""
                var options = document.querySelectorAll('[role="option"], [role="listbox"] li, .dropdown-option, .select-option, .checkbox-option');
                for (var i = 0; i < options.length; i++) {{
                    var text = options[i].textContent.trim().toLowerCase();
                    var dataVal = options[i].getAttribute('data-value') || '';
                    if (text.includes('{str(val).lower()}') || dataVal.toLowerCase().includes('{str(val).lower()}')) {{
                        options[i].click();
                        return true;
                    }}
                }}
                return false;
                """
                result = self.driver.execute_script(js)
                if result:
                    selected_count += 1
                    time.sleep(0.2)
            except Exception:
                continue
        
        try:
            element.send_keys(Keys.ESCAPE)
        except Exception:
            pass
        
        return selected_count > 0


class SelectAutocompleteAction(BaseAction):
    action_type = ActionType.SELECT_OPTION
    
    def execute(self, command: FillCommand) -> FillResult:
        start = time.time()
        
        try:
            element = self.locator.find_visible(
                command.selector,
                command.selector_type,
                command.timeout_ms,
            )
            
            self.locator.scroll_into_view(element)
            
            value = str(command.value)
            
            try:
                element.click()
            except Exception:
                self.driver.execute_script("arguments[0].click();", element)
            
            time.sleep(0.2)
            
            try:
                element.clear()
            except Exception:
                pass
            
            element.send_keys(value)
            time.sleep(0.5)
            
            suggestion_selectors = [
                "[role='listbox'] [role='option']",
                ".autocomplete-suggestion",
                ".suggestion-item",
                ".dropdown-item",
                ".pac-item",
                "[class*='suggestion']",
                "[class*='option']",
            ]
            
            for selector in suggestion_selectors:
                try:
                    suggestions = self.driver.find_elements(By.CSS_SELECTOR, selector)
                    if suggestions:
                        for suggestion in suggestions:
                            if suggestion.is_displayed():
                                text = suggestion.text.lower()
                                if value.lower() in text:
                                    suggestion.click()
                                    self._wait_after(command)
                                    
                                    duration = int((time.time() - start) * 1000)
                                    return self._create_result(
                                        command,
                                        success=True,
                                        value_used=suggestion.text,
                                        duration_ms=duration,
                                    )
                except Exception:
                    continue
            
            element.send_keys(Keys.DOWN)
            time.sleep(0.1)
            element.send_keys(Keys.ENTER)
            
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
