import pytest
from unittest.mock import Mock, patch, MagicMock
import tempfile
import os

from autofill import AutofillEngine
from autofill.models import ActionType, FillCommand


class TestIntegrationFormFilling:
    @pytest.fixture
    def engine(self, mock_driver):
        return AutofillEngine(mock_driver)
    
    @patch('autofill.locator.WebDriverWait')
    def test_complete_job_application_form(self, mock_wait_class, engine, mock_element):
        mock_wait = Mock()
        mock_wait.until.return_value = mock_element
        mock_wait_class.return_value = mock_wait
        mock_element.get_attribute.return_value = "text"
        mock_element.tag_name = "input"
        
        commands = [
            {"action": "type_text", "selector": "#first_name", "value": "John"},
            {"action": "type_text", "selector": "#last_name", "value": "Doe"},
            {"action": "type_text", "selector": "#email", "value": "john.doe@example.com"},
            {"action": "type_text", "selector": "#phone", "value": "+1-555-123-4567"},
            {"action": "type_text", "selector": "#address", "value": "123 Main St"},
            {"action": "type_text", "selector": "#city", "value": "New York"},
            {"action": "type_text", "selector": "#zip", "value": "10001"},
        ]
        
        results = engine.execute_all(commands)
        
        assert len(results) == 7
        summary = engine.get_results_summary(results)
        assert summary["failed"] == 0
    
    @patch('autofill.actions.select.Select')
    @patch('autofill.locator.WebDriverWait')
    def test_form_with_dropdowns(self, mock_wait_class, mock_select_class, engine, mock_element):
        mock_wait = Mock()
        mock_element.tag_name = "select"
        mock_wait.until.return_value = mock_element
        mock_wait_class.return_value = mock_wait
        
        mock_select = Mock()
        mock_select_class.return_value = mock_select
        
        commands = [
            {"action": "select_option", "selector": "#country", "value": "US", "select_by": "value"},
            {"action": "select_option", "selector": "#state", "value": "NY", "select_by": "value"},
            {"action": "select_option", "selector": "#experience", "value": "5+ years", "select_by": "text"},
        ]
        
        results = engine.execute_all(commands)
        
        assert len(results) == 3
    
    @patch('autofill.locator.WebDriverWait')
    def test_form_with_checkboxes_and_radios(self, mock_wait_class, engine, mock_element):
        mock_wait = Mock()
        mock_wait.until.return_value = mock_element
        mock_wait_class.return_value = mock_wait
        mock_element.get_attribute.side_effect = lambda attr: {
            "type": "checkbox",
            "role": None,
        }.get(attr)
        mock_element.is_selected.return_value = False
        
        commands = [
            {"action": "check", "selector": "#terms", "checked": True},
            {"action": "check", "selector": "#newsletter", "checked": False},
            {"action": "select_radio", "name": "work_auth", "value": "yes"},
            {"action": "select_radio", "name": "remote", "value": "hybrid"},
        ]
        
        results = engine.execute_all(commands)
        
        assert len(results) == 4
    
    @patch('autofill.locator.WebDriverWait')
    def test_form_with_file_upload(self, mock_wait_class, engine, mock_element):
        mock_wait = Mock()
        mock_wait.until.return_value = mock_element
        mock_wait_class.return_value = mock_wait
        mock_element.get_attribute.return_value = "file"
        
        with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as f:
            f.write(b"fake pdf content")
            resume_path = f.name
        
        with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as f:
            f.write(b"fake cover letter")
            cover_letter_path = f.name
        
        try:
            commands = [
                {"action": "upload_file", "selector": "#resume", "file_path": resume_path},
                {"action": "upload_file", "selector": "#cover_letter", "file_path": cover_letter_path},
            ]
            
            results = engine.execute_all(commands)
            
            assert len(results) == 2
            assert all(r.success for r in results)
        finally:
            os.unlink(resume_path)
            os.unlink(cover_letter_path)
    
    @patch('autofill.locator.WebDriverWait')
    def test_form_navigation(self, mock_wait_class, engine, mock_element):
        mock_wait = Mock()
        mock_wait.until.return_value = mock_element
        mock_wait_class.return_value = mock_wait
        
        commands = [
            {"action": "type_text", "selector": "#step1_field", "value": "Step 1 data"},
            {"action": "click", "selector": "#next_btn"},
            {"action": "wait", "time_ms": 100},
            {"action": "type_text", "selector": "#step2_field", "value": "Step 2 data"},
            {"action": "click", "selector": "#next_btn"},
            {"action": "wait", "time_ms": 100},
            {"action": "click", "selector": "#submit_btn"},
        ]
        
        results = engine.execute_all(commands)
        
        assert len(results) == 7


class TestIntegrationEdgeCases:
    @pytest.fixture
    def engine(self, mock_driver):
        return AutofillEngine(mock_driver)
    
    @patch('autofill.locator.WebDriverWait')
    def test_retry_on_failure(self, mock_wait_class, engine, mock_element):
        call_count = [0]
        
        def mock_until(condition):
            call_count[0] += 1
            if call_count[0] < 3:
                raise Exception("Temporary failure")
            return mock_element
        
        mock_wait = Mock()
        mock_wait.until = mock_until
        mock_wait_class.return_value = mock_wait
        
        engine.configure(retry_count=3, retry_delay_ms=10)
        
        result = engine.execute({
            "action": "click",
            "selector": "#button",
        })
        
        assert result.success == True
    
    @patch('autofill.locator.WebDriverWait')
    def test_timeout_handling(self, mock_wait_class, engine):
        mock_wait = Mock()
        mock_wait.until.side_effect = Exception("Timeout")
        mock_wait_class.return_value = mock_wait
        
        result = engine.execute({
            "action": "click",
            "selector": "#nonexistent",
            "timeout_ms": 100,
        })
        
        assert result.success == False
        assert result.element_found == False
    
    @patch('autofill.locator.WebDriverWait')
    def test_special_characters_in_value(self, mock_wait_class, engine, mock_element):
        mock_wait = Mock()
        mock_wait.until.return_value = mock_element
        mock_wait_class.return_value = mock_wait
        
        special_values = [
            "O'Connor",
            "test@example.com",
            "Line 1\nLine 2",
            "Tab\there",
            "Quotes \"inside\"",
            "Backslash \\",
            "Unicode: 日本語",
        ]
        
        for value in special_values:
            result = engine.type_text("#input", value)
            assert result.success == True, f"Failed for value: {value}"
    
    @patch('autofill.locator.WebDriverWait')
    def test_empty_value(self, mock_wait_class, engine, mock_element):
        mock_wait = Mock()
        mock_wait.until.return_value = mock_element
        mock_wait_class.return_value = mock_wait
        
        result = engine.type_text("#input", "")
        
        assert result.success == True
        assert result.value_used == ""
    
    @patch('autofill.locator.WebDriverWait')
    def test_none_value(self, mock_wait_class, engine, mock_element):
        mock_wait = Mock()
        mock_wait.until.return_value = mock_element
        mock_wait_class.return_value = mock_wait
        
        result = engine.execute({
            "action": "type_text",
            "selector": "#input",
            "value": None,
        })
        
        assert result.success == True
        assert result.value_used == ""


class TestIntegrationKeyboardActions:
    @pytest.fixture
    def engine(self, mock_driver):
        return AutofillEngine(mock_driver)
    
    @patch('autofill.actions.utility.ActionChains')
    def test_keyboard_shortcuts(self, mock_action_chains, engine):
        mock_actions = Mock()
        mock_action_chains.return_value = mock_actions
        mock_actions.key_down.return_value = mock_actions
        mock_actions.key_up.return_value = mock_actions
        mock_actions.send_keys.return_value = mock_actions
        
        shortcuts = [
            "ctrl+a",
            "ctrl+c",
            "ctrl+v",
            "ctrl+z",
            "shift+tab",
            "alt+f4",
        ]
        
        for shortcut in shortcuts:
            result = engine.press_key(shortcut)
            assert result.success == True, f"Failed for shortcut: {shortcut}"
    
    @patch('autofill.actions.utility.ActionChains')
    def test_special_keys(self, mock_action_chains, engine):
        mock_actions = Mock()
        mock_action_chains.return_value = mock_actions
        mock_actions.send_keys.return_value = mock_actions
        
        keys = [
            "enter", "tab", "escape", "backspace", "delete",
            "up", "down", "left", "right",
            "home", "end", "pageup", "pagedown",
        ]
        
        for key in keys:
            result = engine.press_key(key)
            assert result.success == True, f"Failed for key: {key}"


class TestIntegrationIframeHandling:
    @pytest.fixture
    def engine(self, mock_driver):
        return AutofillEngine(mock_driver)
    
    @patch('autofill.locator.WebDriverWait')
    def test_switch_to_iframe_and_fill(self, mock_wait_class, engine, mock_element, mock_driver):
        mock_wait = Mock()
        mock_wait.until.return_value = mock_element
        mock_wait_class.return_value = mock_wait
        
        commands = [
            {"action": "switch_iframe", "selector": "#app-iframe"},
            {"action": "type_text", "selector": "#inner_field", "value": "Inside iframe"},
            {"action": "click", "selector": "#inner_button"},
            {"action": "switch_default"},
            {"action": "click", "selector": "#outer_button"},
        ]
        
        results = engine.execute_all(commands)
        
        assert len(results) == 5
        mock_driver.switch_to.frame.assert_called()
        mock_driver.switch_to.default_content.assert_called()


class TestIntegrationDateHandling:
    @pytest.fixture
    def engine(self, mock_driver):
        return AutofillEngine(mock_driver)
    
    @patch('autofill.locator.WebDriverWait')
    def test_various_date_formats(self, mock_wait_class, engine, mock_element):
        mock_wait = Mock()
        mock_wait.until.return_value = mock_element
        mock_wait_class.return_value = mock_wait
        mock_element.get_attribute.return_value = "text"
        
        date_tests = [
            ("2024-01-15", "YYYY-MM-DD", "2024-01-15"),
            ("2024-01-15", "MM/DD/YYYY", "01/15/2024"),
            ("2024-01-15", "DD/MM/YYYY", "15/01/2024"),
        ]
        
        for input_date, format_str, expected in date_tests:
            result = engine.enter_date("#date_field", input_date, date_format=format_str)
            assert result.success == True, f"Failed for format: {format_str}"
            assert result.value_used == expected, f"Expected {expected}, got {result.value_used}"


class TestIntegrationBatchOperations:
    @pytest.fixture
    def engine(self, mock_driver):
        return AutofillEngine(mock_driver)
    
    @patch('autofill.locator.WebDriverWait')
    def test_large_form(self, mock_wait_class, engine, mock_element):
        mock_wait = Mock()
        mock_wait.until.return_value = mock_element
        mock_wait_class.return_value = mock_wait
        
        commands = [
            {"action": "type_text", "selector": f"#field_{i}", "value": f"Value {i}"}
            for i in range(50)
        ]
        
        results = engine.execute_all(commands)
        
        assert len(results) == 50
        summary = engine.get_results_summary(results)
        assert summary["total"] == 50
    
    @patch('autofill.locator.WebDriverWait')
    def test_mixed_actions_batch(self, mock_wait_class, engine, mock_element):
        mock_wait = Mock()
        mock_wait.until.return_value = mock_element
        mock_wait_class.return_value = mock_wait
        mock_element.get_attribute.return_value = "text"
        mock_element.is_selected.return_value = False
        
        commands = [
            {"action": "scroll_to", "selector": "#form_start"},
            {"action": "type_text", "selector": "#name", "value": "John"},
            {"action": "focus", "selector": "#email"},
            {"action": "type_text", "selector": "#email", "value": "john@example.com"},
            {"action": "blur", "selector": "#email"},
            {"action": "wait", "time_ms": 50},
            {"action": "check", "selector": "#agree", "checked": True},
            {"action": "scroll_to", "selector": "#submit"},
            {"action": "click", "selector": "#submit"},
        ]
        
        results = engine.execute_all(commands)
        
        assert len(results) == 9

