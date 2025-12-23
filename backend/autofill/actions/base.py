import time
from abc import ABC, abstractmethod
from typing import Any

from selenium.webdriver.remote.webdriver import WebDriver

from autofill.models import FillCommand, FillResult, ActionType
from autofill.locator import ElementLocator
from autofill.exceptions import ActionExecutionError


class BaseAction(ABC):
    action_type: ActionType = None
    
    def __init__(self, driver: WebDriver):
        self.driver = driver
        self.locator = ElementLocator(driver)
    
    @abstractmethod
    def execute(self, command: FillCommand) -> FillResult:
        pass
    
    def _create_result(
        self,
        command: FillCommand,
        success: bool,
        value_used: Any = None,
        element_found: bool = True,
        error: str = None,
        duration_ms: int = 0,
    ) -> FillResult:
        return FillResult(
            success=success,
            action=command.action,
            selector=command.selector,
            value_used=value_used,
            element_found=element_found,
            error=error,
            duration_ms=duration_ms,
        )
    
    def _wait_after(self, command: FillCommand) -> None:
        if command.wait_after_ms > 0:
            time.sleep(command.wait_after_ms / 1000)

