import pytest
from autofill.exceptions import (
    AutofillError,
    ElementNotFoundError,
    ActionExecutionError,
    InvalidCommandError,
    TimeoutError,
)


class TestAutofillError:
    def test_base_error(self):
        error = AutofillError("Test error")
        assert str(error) == "Test error"
        assert isinstance(error, Exception)


class TestElementNotFoundError:
    def test_css_selector(self):
        error = ElementNotFoundError("#email", "css")
        assert error.selector == "#email"
        assert error.selector_type == "css"
        assert "Element not found" in str(error)
        assert "#email" in str(error)
    
    def test_xpath_selector(self):
        error = ElementNotFoundError("//input[@id='email']", "xpath")
        assert error.selector_type == "xpath"
    
    def test_default_selector_type(self):
        error = ElementNotFoundError("#button")
        assert error.selector_type == "css"


class TestActionExecutionError:
    def test_action_error(self):
        error = ActionExecutionError("type_text", "Cannot type into disabled element")
        assert error.action == "type_text"
        assert "type_text" in str(error)
        assert "Cannot type into disabled element" in str(error)


class TestInvalidCommandError:
    def test_invalid_command(self):
        error = InvalidCommandError("Missing required field: action")
        assert "Invalid command" in str(error)
        assert "Missing required field" in str(error)


class TestTimeoutError:
    def test_timeout(self):
        error = TimeoutError("Element not visible within 10 seconds")
        assert "Timeout" in str(error)
        assert "10 seconds" in str(error)


class TestErrorInheritance:
    def test_all_errors_inherit_from_autofill_error(self):
        assert issubclass(ElementNotFoundError, AutofillError)
        assert issubclass(ActionExecutionError, AutofillError)
        assert issubclass(InvalidCommandError, AutofillError)
        assert issubclass(TimeoutError, AutofillError)

