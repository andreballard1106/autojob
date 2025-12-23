class AutofillError(Exception):
    pass


class ElementNotFoundError(AutofillError):
    def __init__(self, selector: str, selector_type: str = "css"):
        self.selector = selector
        self.selector_type = selector_type
        super().__init__(f"Element not found: {selector_type}={selector}")


class ActionExecutionError(AutofillError):
    def __init__(self, action: str, message: str):
        self.action = action
        super().__init__(f"Action '{action}' failed: {message}")


class InvalidCommandError(AutofillError):
    def __init__(self, message: str):
        super().__init__(f"Invalid command: {message}")


class TimeoutError(AutofillError):
    def __init__(self, message: str):
        super().__init__(f"Timeout: {message}")

