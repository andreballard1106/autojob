import pytest
from unittest.mock import Mock, patch, MagicMock

from autofill.engine import AutofillEngine
from autofill.models import FillCommand, FillResult, ActionType


class TestAutofillEngineInit:
    def test_init(self, mock_driver):
        engine = AutofillEngine(mock_driver)
        
        assert engine.driver == mock_driver
        assert engine.registry is not None
        assert engine._stop_on_error == False
        assert engine._retry_count == 0
    
    def test_configure(self, mock_driver):
        engine = AutofillEngine(mock_driver)
        
        engine.configure(
            stop_on_error=True,
            retry_count=3,
            retry_delay_ms=1000,
        )
        
        assert engine._stop_on_error == True
        assert engine._retry_count == 3
        assert engine._retry_delay_ms == 1000
    
    def test_configure_returns_self(self, mock_driver):
        engine = AutofillEngine(mock_driver)
        
        result = engine.configure(stop_on_error=True)
        
        assert result is engine


class TestAutofillEngineExecute:
    @pytest.fixture
    def engine(self, mock_driver):
        return AutofillEngine(mock_driver)
    
    @patch('autofill.locator.WebDriverWait')
    def test_execute_dict_command(self, mock_wait_class, engine, mock_element):
        mock_wait = Mock()
        mock_wait.until.return_value = mock_element
        mock_wait_class.return_value = mock_wait
        mock_element.get_attribute.return_value = "test@example.com"
        
        result = engine.execute({
            "action": "type_text",
            "selector": "#email",
            "value": "test@example.com",
        })
        
        assert result.success == True
        assert result.action == ActionType.TYPE_TEXT
    
    @patch('autofill.locator.WebDriverWait')
    def test_execute_fill_command(self, mock_wait_class, engine, mock_element):
        mock_wait = Mock()
        mock_wait.until.return_value = mock_element
        mock_wait_class.return_value = mock_wait
        
        command = FillCommand(
            action=ActionType.CLICK,
            selector="#button",
        )
        
        result = engine.execute(command)
        
        assert result.success == True
    
    def test_execute_invalid_dict(self, engine):
        result = engine.execute({
            "action": "invalid_action",
            "selector": "#test",
        })
        
        assert result.success == False
        assert "Invalid" in result.error or "Unknown" in str(result.error) or result.error is not None


class TestAutofillEngineExecuteAll:
    @pytest.fixture
    def engine(self, mock_driver):
        return AutofillEngine(mock_driver)
    
    @patch('autofill.locator.WebDriverWait')
    def test_execute_all_success(self, mock_wait_class, engine, mock_element):
        mock_wait = Mock()
        mock_wait.until.return_value = mock_element
        mock_wait_class.return_value = mock_wait
        mock_element.get_attribute.return_value = "value"
        
        commands = [
            {"action": "type_text", "selector": "#first", "value": "John"},
            {"action": "type_text", "selector": "#last", "value": "Doe"},
            {"action": "click", "selector": "#submit"},
        ]
        
        results = engine.execute_all(commands)
        
        assert len(results) == 3
        assert all(r.success for r in results)
    
    @patch('autofill.locator.WebDriverWait')
    def test_execute_all_stop_on_error(self, mock_wait_class, engine, mock_element):
        mock_wait = Mock()
        mock_wait.until.side_effect = [mock_element, Exception("Not found"), mock_element]
        mock_wait_class.return_value = mock_wait
        
        engine.configure(stop_on_error=True)
        
        commands = [
            {"action": "type_text", "selector": "#first", "value": "John"},
            {"action": "type_text", "selector": "#nonexistent", "value": "test"},
            {"action": "click", "selector": "#submit"},
        ]
        
        results = engine.execute_all(commands)
        
        assert len(results) == 2
        assert results[0].success == True
        assert results[1].success == False
    
    @patch('autofill.locator.WebDriverWait')
    def test_execute_all_continue_on_error(self, mock_wait_class, engine, mock_element):
        call_count = [0]
        
        def mock_until(condition):
            call_count[0] += 1
            if call_count[0] == 2:
                raise Exception("Not found")
            return mock_element
        
        mock_wait = Mock()
        mock_wait.until = mock_until
        mock_wait_class.return_value = mock_wait
        
        engine.configure(stop_on_error=False)
        
        commands = [
            {"action": "type_text", "selector": "#first", "value": "John"},
            {"action": "type_text", "selector": "#nonexistent", "value": "test"},
            {"action": "click", "selector": "#submit"},
        ]
        
        results = engine.execute_all(commands)
        
        assert len(results) == 3


class TestAutofillEngineHelperMethods:
    @pytest.fixture
    def engine(self, mock_driver):
        return AutofillEngine(mock_driver)
    
    @patch('autofill.locator.WebDriverWait')
    def test_type_text(self, mock_wait_class, engine, mock_element):
        mock_wait = Mock()
        mock_wait.until.return_value = mock_element
        mock_wait_class.return_value = mock_wait
        
        result = engine.type_text("#email", "test@example.com")
        
        assert result.action == ActionType.TYPE_TEXT
    
    @patch('autofill.locator.WebDriverWait')
    def test_type_number(self, mock_wait_class, engine, mock_element):
        mock_wait = Mock()
        mock_wait.until.return_value = mock_element
        mock_wait_class.return_value = mock_wait
        
        result = engine.type_number("#age", 25)
        
        assert result.action == ActionType.TYPE_NUMBER
    
    @patch('autofill.locator.WebDriverWait')
    @patch('autofill.actions.select.Select')
    def test_select_option(self, mock_select_class, mock_wait_class, engine, mock_element):
        mock_wait = Mock()
        mock_element.tag_name = "select"
        mock_wait.until.return_value = mock_element
        mock_wait_class.return_value = mock_wait
        mock_select = Mock()
        mock_select_class.return_value = mock_select
        
        result = engine.select_option("#country", "US")
        
        assert result.action == ActionType.SELECT_OPTION
    
    @patch('autofill.locator.WebDriverWait')
    def test_check(self, mock_wait_class, engine, mock_element):
        mock_wait = Mock()
        mock_wait.until.return_value = mock_element
        mock_wait_class.return_value = mock_wait
        mock_element.get_attribute.return_value = "checkbox"
        mock_element.is_selected.return_value = False
        
        result = engine.check("#agree", True)
        
        assert result.action == ActionType.CHECK
    
    @patch('autofill.locator.WebDriverWait')
    def test_click(self, mock_wait_class, engine, mock_element):
        mock_wait = Mock()
        mock_wait.until.return_value = mock_element
        mock_wait_class.return_value = mock_wait
        
        result = engine.click("#submit")
        
        assert result.action == ActionType.CLICK
    
    @patch('autofill.locator.WebDriverWait')
    def test_clear(self, mock_wait_class, engine, mock_element):
        mock_wait = Mock()
        mock_wait.until.return_value = mock_element
        mock_wait_class.return_value = mock_wait
        
        result = engine.clear("#input")
        
        assert result.action == ActionType.CLEAR
    
    def test_wait_time(self, engine):
        result = engine.wait(time_ms=50)
        
        assert result.success == True
        assert result.action == ActionType.WAIT
    
    @patch('autofill.actions.utility.ActionChains')
    def test_press_key(self, mock_action_chains, engine):
        mock_actions = Mock()
        mock_action_chains.return_value = mock_actions
        mock_actions.send_keys.return_value = mock_actions
        
        result = engine.press_key("enter")
        
        assert result.action == ActionType.PRESS_KEY
    
    @patch('autofill.actions.utility.ActionChains')
    @patch('autofill.locator.WebDriverWait')
    def test_hover(self, mock_wait_class, mock_action_chains, engine, mock_element):
        mock_wait = Mock()
        mock_wait.until.return_value = mock_element
        mock_wait_class.return_value = mock_wait
        
        mock_actions = Mock()
        mock_action_chains.return_value = mock_actions
        mock_actions.move_to_element.return_value = mock_actions
        
        result = engine.hover("#menu")
        
        assert result.action == ActionType.HOVER
    
    @patch('autofill.locator.WebDriverWait')
    def test_focus(self, mock_wait_class, engine, mock_element):
        mock_wait = Mock()
        mock_wait.until.return_value = mock_element
        mock_wait_class.return_value = mock_wait
        
        result = engine.focus("#input")
        
        assert result.action == ActionType.FOCUS
    
    @patch('autofill.locator.WebDriverWait')
    def test_blur(self, mock_wait_class, engine, mock_element):
        mock_wait = Mock()
        mock_wait.until.return_value = mock_element
        mock_wait_class.return_value = mock_wait
        
        result = engine.blur("#input")
        
        assert result.action == ActionType.BLUR
    
    @patch('autofill.locator.WebDriverWait')
    def test_scroll_to(self, mock_wait_class, engine, mock_element):
        mock_wait = Mock()
        mock_wait.until.return_value = mock_element
        mock_wait_class.return_value = mock_wait
        
        result = engine.scroll_to("#section")
        
        assert result.action == ActionType.SCROLL_TO
    
    @patch('autofill.locator.WebDriverWait')
    def test_set_value(self, mock_wait_class, engine, mock_element, mock_driver):
        mock_wait = Mock()
        mock_wait.until.return_value = mock_element
        mock_wait_class.return_value = mock_wait
        
        result = engine.set_value("#input", "test value")
        
        assert result.action == ActionType.SET_VALUE
    
    def test_execute_js(self, engine, mock_driver):
        result = engine.execute_js("return document.title;")
        
        assert result.action == ActionType.EXECUTE_JS
    
    @patch('autofill.locator.WebDriverWait')
    def test_switch_iframe(self, mock_wait_class, engine, mock_element, mock_driver):
        mock_wait = Mock()
        mock_wait.until.return_value = mock_element
        mock_wait_class.return_value = mock_wait
        
        result = engine.switch_iframe("#myframe")
        
        assert result.action == ActionType.SWITCH_IFRAME
        mock_driver.switch_to.frame.assert_called()
    
    def test_switch_default(self, engine, mock_driver):
        result = engine.switch_default()
        
        assert result.action == ActionType.SWITCH_DEFAULT
        mock_driver.switch_to.default_content.assert_called()


class TestAutofillEngineFillForm:
    @pytest.fixture
    def engine(self, mock_driver):
        return AutofillEngine(mock_driver)
    
    @patch('autofill.locator.WebDriverWait')
    def test_fill_form_simple(self, mock_wait_class, engine, mock_element):
        mock_wait = Mock()
        mock_wait.until.return_value = mock_element
        mock_wait_class.return_value = mock_wait
        
        fields = {
            "#first_name": "John",
            "#last_name": "Doe",
            "#email": "john@example.com",
        }
        
        results = engine.fill_form(fields)
        
        assert len(results) == 3
        assert "#first_name" in results
        assert "#last_name" in results
        assert "#email" in results
    
    @patch('autofill.locator.WebDriverWait')
    @patch('autofill.actions.select.Select')
    def test_fill_form_with_options(self, mock_select_class, mock_wait_class, engine, mock_element):
        mock_wait = Mock()
        mock_element.tag_name = "select"
        mock_wait.until.return_value = mock_element
        mock_wait_class.return_value = mock_wait
        mock_select = Mock()
        mock_select_class.return_value = mock_select
        
        fields = {
            "#name": "John Doe",
            "#country": {
                "action": "select_option",
                "value": "US",
                "select_by": "value",
            },
        }
        
        results = engine.fill_form(fields)
        
        assert len(results) == 2


class TestAutofillEngineResultsSummary:
    @pytest.fixture
    def engine(self, mock_driver):
        return AutofillEngine(mock_driver)
    
    def test_get_results_summary_all_success(self, engine):
        results = [
            FillResult(success=True, action=ActionType.TYPE_TEXT, selector="#a", duration_ms=100),
            FillResult(success=True, action=ActionType.TYPE_TEXT, selector="#b", duration_ms=150),
            FillResult(success=True, action=ActionType.CLICK, selector="#c", duration_ms=50),
        ]
        
        summary = engine.get_results_summary(results)
        
        assert summary["total"] == 3
        assert summary["successful"] == 3
        assert summary["failed"] == 0
        assert summary["success_rate"] == 1.0
        assert summary["total_duration_ms"] == 300
        assert len(summary["failures"]) == 0
    
    def test_get_results_summary_with_failures(self, engine):
        results = [
            FillResult(success=True, action=ActionType.TYPE_TEXT, selector="#a", duration_ms=100),
            FillResult(success=False, action=ActionType.TYPE_TEXT, selector="#b", error="Not found", duration_ms=5000),
            FillResult(success=True, action=ActionType.CLICK, selector="#c", duration_ms=50),
        ]
        
        summary = engine.get_results_summary(results)
        
        assert summary["total"] == 3
        assert summary["successful"] == 2
        assert summary["failed"] == 1
        assert summary["success_rate"] == 2/3
        assert len(summary["failures"]) == 1
        assert summary["failures"][0]["selector"] == "#b"
        assert summary["failures"][0]["error"] == "Not found"
    
    def test_get_results_summary_empty(self, engine):
        results = []
        
        summary = engine.get_results_summary(results)
        
        assert summary["total"] == 0
        assert summary["successful"] == 0
        assert summary["failed"] == 0
        assert summary["success_rate"] == 0

