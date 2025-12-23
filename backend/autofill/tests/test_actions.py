import pytest
from unittest.mock import Mock, patch, MagicMock
import os
import tempfile

from autofill.models import FillCommand, ActionType, SelectorType, SelectBy
from autofill.actions.text import TypeTextAction, TypeNumberAction
from autofill.actions.select import SelectOptionAction, SelectMultipleAction
from autofill.actions.checkbox import CheckAction, SelectRadioAction
from autofill.actions.file import UploadFileAction
from autofill.actions.date import EnterDateAction
from autofill.actions.click import ClickAction, DoubleClickAction, RightClickAction
from autofill.actions.utility import (
    ClearAction, FocusAction, BlurAction, ScrollToAction,
    WaitAction, PressKeyAction, HoverAction, SetValueAction,
)


class TestTypeTextAction:
    @pytest.fixture
    def action(self, mock_driver):
        return TypeTextAction(mock_driver)
    
    @patch('autofill.locator.WebDriverWait')
    def test_type_text_success(self, mock_wait_class, action, mock_element):
        mock_wait = Mock()
        mock_wait.until.return_value = mock_element
        mock_wait_class.return_value = mock_wait
        mock_element.get_attribute.return_value = "test@example.com"
        
        command = FillCommand(
            action=ActionType.TYPE_TEXT,
            selector="#email",
            value="test@example.com",
        )
        
        result = action.execute(command)
        
        assert result.success == True
        assert result.value_used == "test@example.com"
        mock_element.send_keys.assert_called()
    
    @patch('autofill.locator.WebDriverWait')
    def test_type_text_with_clear(self, mock_wait_class, action, mock_element):
        mock_wait = Mock()
        mock_wait.until.return_value = mock_element
        mock_wait_class.return_value = mock_wait
        
        command = FillCommand(
            action=ActionType.TYPE_TEXT,
            selector="#email",
            value="new@example.com",
            clear_first=True,
        )
        
        result = action.execute(command)
        
        assert result.success == True
        mock_element.clear.assert_called()
    
    @patch('autofill.locator.WebDriverWait')
    def test_type_text_not_found(self, mock_wait_class, action):
        mock_wait = Mock()
        mock_wait.until.side_effect = Exception("Not found")
        mock_wait_class.return_value = mock_wait
        
        command = FillCommand(
            action=ActionType.TYPE_TEXT,
            selector="#nonexistent",
            value="test",
        )
        
        result = action.execute(command)
        
        assert result.success == False
        assert result.element_found == False


class TestTypeNumberAction:
    @pytest.fixture
    def action(self, mock_driver):
        return TypeNumberAction(mock_driver)
    
    @patch('autofill.locator.WebDriverWait')
    def test_type_number_integer(self, mock_wait_class, action, mock_element):
        mock_wait = Mock()
        mock_wait.until.return_value = mock_element
        mock_wait_class.return_value = mock_wait
        mock_element.get_attribute.return_value = "25"
        
        command = FillCommand(
            action=ActionType.TYPE_NUMBER,
            selector="#age",
            value=25,
        )
        
        result = action.execute(command)
        
        assert result.success == True
        assert result.value_used == "25"
    
    @patch('autofill.locator.WebDriverWait')
    def test_type_number_float(self, mock_wait_class, action, mock_element):
        mock_wait = Mock()
        mock_wait.until.return_value = mock_element
        mock_wait_class.return_value = mock_wait
        mock_element.get_attribute.return_value = "99.99"
        
        command = FillCommand(
            action=ActionType.TYPE_NUMBER,
            selector="#price",
            value=99.99,
        )
        
        result = action.execute(command)
        
        assert result.success == True


class TestSelectOptionAction:
    @pytest.fixture
    def action(self, mock_driver):
        return SelectOptionAction(mock_driver)
    
    @patch('autofill.locator.WebDriverWait')
    @patch('autofill.actions.select.Select')
    def test_select_by_value(self, mock_select_class, mock_wait_class, action, mock_select_element):
        mock_wait = Mock()
        mock_wait.until.return_value = mock_select_element
        mock_wait_class.return_value = mock_wait
        
        mock_select = Mock()
        mock_select_class.return_value = mock_select
        
        command = FillCommand(
            action=ActionType.SELECT_OPTION,
            selector="#country",
            value="US",
            select_by=SelectBy.VALUE,
        )
        
        result = action.execute(command)
        
        assert result.success == True
        mock_select.select_by_value.assert_called_with("US")
    
    @patch('autofill.locator.WebDriverWait')
    @patch('autofill.actions.select.Select')
    def test_select_by_text(self, mock_select_class, mock_wait_class, action, mock_select_element):
        mock_wait = Mock()
        mock_wait.until.return_value = mock_select_element
        mock_wait_class.return_value = mock_wait
        
        mock_select = Mock()
        mock_select_class.return_value = mock_select
        
        command = FillCommand(
            action=ActionType.SELECT_OPTION,
            selector="#country",
            value="United States",
            select_by=SelectBy.TEXT,
        )
        
        result = action.execute(command)
        
        assert result.success == True
        mock_select.select_by_visible_text.assert_called_with("United States")
    
    @patch('autofill.locator.WebDriverWait')
    @patch('autofill.actions.select.Select')
    def test_select_by_index(self, mock_select_class, mock_wait_class, action, mock_select_element):
        mock_wait = Mock()
        mock_wait.until.return_value = mock_select_element
        mock_wait_class.return_value = mock_wait
        
        mock_select = Mock()
        mock_select_class.return_value = mock_select
        
        command = FillCommand(
            action=ActionType.SELECT_OPTION,
            selector="#country",
            value=2,
            select_by=SelectBy.INDEX,
        )
        
        result = action.execute(command)
        
        assert result.success == True
        mock_select.select_by_index.assert_called_with(2)


class TestCheckAction:
    @pytest.fixture
    def action(self, mock_driver):
        return CheckAction(mock_driver)
    
    @patch('autofill.locator.WebDriverWait')
    def test_check_checkbox(self, mock_wait_class, action, mock_checkbox_element):
        mock_wait = Mock()
        mock_wait.until.return_value = mock_checkbox_element
        mock_wait_class.return_value = mock_wait
        mock_checkbox_element.is_selected.return_value = False
        
        command = FillCommand(
            action=ActionType.CHECK,
            selector="#agree",
            checked=True,
        )
        
        result = action.execute(command)
        
        assert result.success == True
        mock_checkbox_element.click.assert_called()
    
    @patch('autofill.locator.WebDriverWait')
    def test_uncheck_checkbox(self, mock_wait_class, action, mock_checkbox_element):
        mock_wait = Mock()
        mock_wait.until.return_value = mock_checkbox_element
        mock_wait_class.return_value = mock_wait
        mock_checkbox_element.is_selected.return_value = True
        
        command = FillCommand(
            action=ActionType.CHECK,
            selector="#agree",
            checked=False,
        )
        
        result = action.execute(command)
        
        assert result.success == True
        mock_checkbox_element.click.assert_called()
    
    @patch('autofill.locator.WebDriverWait')
    def test_checkbox_already_checked(self, mock_wait_class, action, mock_checkbox_element):
        mock_wait = Mock()
        mock_wait.until.return_value = mock_checkbox_element
        mock_wait_class.return_value = mock_wait
        mock_checkbox_element.is_selected.return_value = True
        
        command = FillCommand(
            action=ActionType.CHECK,
            selector="#agree",
            checked=True,
        )
        
        result = action.execute(command)
        
        assert result.success == True
        mock_checkbox_element.click.assert_not_called()


class TestSelectRadioAction:
    @pytest.fixture
    def action(self, mock_driver):
        return SelectRadioAction(mock_driver)
    
    @patch('autofill.locator.WebDriverWait')
    def test_select_radio_by_name_value(self, mock_wait_class, action, mock_radio_element, mock_driver):
        mock_wait = Mock()
        mock_wait.until.return_value = mock_radio_element
        mock_wait_class.return_value = mock_wait
        mock_radio_element.is_selected.return_value = False
        
        command = FillCommand(
            action=ActionType.SELECT_RADIO,
            name="gender",
            value="male",
        )
        
        result = action.execute(command)
        
        assert result.success == True


class TestUploadFileAction:
    @pytest.fixture
    def action(self, mock_driver):
        return UploadFileAction(mock_driver)
    
    @patch('autofill.locator.WebDriverWait')
    def test_upload_file_success(self, mock_wait_class, action, mock_file_element):
        mock_wait = Mock()
        mock_wait.until.return_value = mock_file_element
        mock_wait_class.return_value = mock_wait
        
        with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as f:
            f.write(b"test content")
            temp_path = f.name
        
        try:
            command = FillCommand(
                action=ActionType.UPLOAD_FILE,
                selector="#resume",
                file_path=temp_path,
            )
            
            result = action.execute(command)
            
            assert result.success == True
            mock_file_element.send_keys.assert_called_with(temp_path)
        finally:
            os.unlink(temp_path)
    
    @patch('autofill.locator.WebDriverWait')
    def test_upload_file_not_found(self, mock_wait_class, action, mock_file_element):
        mock_wait = Mock()
        mock_wait.until.return_value = mock_file_element
        mock_wait_class.return_value = mock_wait
        
        command = FillCommand(
            action=ActionType.UPLOAD_FILE,
            selector="#resume",
            file_path="/nonexistent/file.pdf",
        )
        
        result = action.execute(command)
        
        assert result.success == False
        assert "File not found" in result.error
    
    def test_upload_no_file_path(self, action):
        command = FillCommand(
            action=ActionType.UPLOAD_FILE,
            selector="#resume",
        )
        
        result = action.execute(command)
        
        assert result.success == False
        assert "No file path" in result.error


class TestEnterDateAction:
    @pytest.fixture
    def action(self, mock_driver):
        return EnterDateAction(mock_driver)
    
    @patch('autofill.locator.WebDriverWait')
    def test_enter_date_text_input(self, mock_wait_class, action, mock_element):
        mock_wait = Mock()
        mock_wait.until.return_value = mock_element
        mock_wait_class.return_value = mock_wait
        mock_element.get_attribute.return_value = "text"
        
        command = FillCommand(
            action=ActionType.ENTER_DATE,
            selector="#start_date",
            value="2024-01-15",
            date_format="YYYY-MM-DD",
        )
        
        result = action.execute(command)
        
        assert result.success == True
    
    @patch('autofill.locator.WebDriverWait')
    def test_enter_date_format_conversion(self, mock_wait_class, action, mock_element):
        mock_wait = Mock()
        mock_wait.until.return_value = mock_element
        mock_wait_class.return_value = mock_wait
        mock_element.get_attribute.return_value = "text"
        
        command = FillCommand(
            action=ActionType.ENTER_DATE,
            selector="#start_date",
            value="2024-01-15",
            date_format="MM/DD/YYYY",
        )
        
        result = action.execute(command)
        
        assert result.success == True
        assert result.value_used == "01/15/2024"


class TestClickAction:
    @pytest.fixture
    def action(self, mock_driver):
        return ClickAction(mock_driver)
    
    @patch('autofill.locator.WebDriverWait')
    def test_click_success(self, mock_wait_class, action, mock_element):
        mock_wait = Mock()
        mock_wait.until.return_value = mock_element
        mock_wait_class.return_value = mock_wait
        
        command = FillCommand(
            action=ActionType.CLICK,
            selector="#submit",
        )
        
        result = action.execute(command)
        
        assert result.success == True
        mock_element.click.assert_called()
    
    @patch('autofill.locator.WebDriverWait')
    def test_click_fallback_to_js(self, mock_wait_class, action, mock_element, mock_driver):
        mock_wait = Mock()
        mock_wait.until.return_value = mock_element
        mock_wait_class.return_value = mock_wait
        mock_element.click.side_effect = Exception("Click intercepted")
        
        command = FillCommand(
            action=ActionType.CLICK,
            selector="#submit",
        )
        
        result = action.execute(command)
        
        assert result.success == True
        mock_driver.execute_script.assert_called()


class TestDoubleClickAction:
    @pytest.fixture
    def action(self, mock_driver):
        return DoubleClickAction(mock_driver)
    
    @patch('autofill.actions.click.ActionChains')
    @patch('autofill.locator.WebDriverWait')
    def test_double_click(self, mock_wait_class, mock_action_chains, action, mock_element):
        mock_wait = Mock()
        mock_wait.until.return_value = mock_element
        mock_wait_class.return_value = mock_wait
        
        mock_actions = Mock()
        mock_action_chains.return_value = mock_actions
        mock_actions.double_click.return_value = mock_actions
        
        command = FillCommand(
            action=ActionType.DOUBLE_CLICK,
            selector="#item",
        )
        
        result = action.execute(command)
        
        assert result.success == True
        mock_actions.double_click.assert_called_with(mock_element)


class TestClearAction:
    @pytest.fixture
    def action(self, mock_driver):
        return ClearAction(mock_driver)
    
    @patch('autofill.locator.WebDriverWait')
    def test_clear_input(self, mock_wait_class, action, mock_element):
        mock_wait = Mock()
        mock_wait.until.return_value = mock_element
        mock_wait_class.return_value = mock_wait
        
        command = FillCommand(
            action=ActionType.CLEAR,
            selector="#email",
        )
        
        result = action.execute(command)
        
        assert result.success == True
        mock_element.clear.assert_called()


class TestWaitAction:
    @pytest.fixture
    def action(self, mock_driver):
        return WaitAction(mock_driver)
    
    def test_wait_time(self, action):
        command = FillCommand(
            action=ActionType.WAIT,
            time_ms=100,
        )
        
        result = action.execute(command)
        
        assert result.success == True
        assert "waited 100ms" in result.value_used
    
    @patch('autofill.locator.WebDriverWait')
    def test_wait_for_visible(self, mock_wait_class, action, mock_element):
        mock_wait = Mock()
        mock_wait.until.return_value = mock_element
        mock_wait_class.return_value = mock_wait
        
        command = FillCommand.from_dict({
            "action": "wait",
            "selector": "#element",
            "condition": "visible",
        })
        
        result = action.execute(command)
        
        assert result.success == True


class TestPressKeyAction:
    @pytest.fixture
    def action(self, mock_driver):
        return PressKeyAction(mock_driver)
    
    @patch('autofill.actions.utility.ActionChains')
    def test_press_enter(self, mock_action_chains, action):
        mock_actions = Mock()
        mock_action_chains.return_value = mock_actions
        mock_actions.send_keys.return_value = mock_actions
        
        command = FillCommand(
            action=ActionType.PRESS_KEY,
            key="enter",
        )
        
        result = action.execute(command)
        
        assert result.success == True
        mock_actions.send_keys.assert_called()
    
    @patch('autofill.actions.utility.ActionChains')
    def test_press_key_combo(self, mock_action_chains, action):
        mock_actions = Mock()
        mock_action_chains.return_value = mock_actions
        mock_actions.key_down.return_value = mock_actions
        mock_actions.key_up.return_value = mock_actions
        mock_actions.send_keys.return_value = mock_actions
        
        command = FillCommand(
            action=ActionType.PRESS_KEY,
            key="ctrl+a",
        )
        
        result = action.execute(command)
        
        assert result.success == True
    
    @patch('autofill.locator.WebDriverWait')
    def test_press_key_on_element(self, mock_wait_class, action, mock_element):
        mock_wait = Mock()
        mock_wait.until.return_value = mock_element
        mock_wait_class.return_value = mock_wait
        
        command = FillCommand(
            action=ActionType.PRESS_KEY,
            selector="#input",
            key="tab",
        )
        
        result = action.execute(command)
        
        assert result.success == True
        mock_element.send_keys.assert_called()


class TestHoverAction:
    @pytest.fixture
    def action(self, mock_driver):
        return HoverAction(mock_driver)
    
    @patch('autofill.actions.utility.ActionChains')
    @patch('autofill.locator.WebDriverWait')
    def test_hover(self, mock_wait_class, mock_action_chains, action, mock_element):
        mock_wait = Mock()
        mock_wait.until.return_value = mock_element
        mock_wait_class.return_value = mock_wait
        
        mock_actions = Mock()
        mock_action_chains.return_value = mock_actions
        mock_actions.move_to_element.return_value = mock_actions
        
        command = FillCommand(
            action=ActionType.HOVER,
            selector="#menu",
        )
        
        result = action.execute(command)
        
        assert result.success == True
        mock_actions.move_to_element.assert_called_with(mock_element)


class TestSetValueAction:
    @pytest.fixture
    def action(self, mock_driver):
        return SetValueAction(mock_driver)
    
    @patch('autofill.locator.WebDriverWait')
    def test_set_value_via_js(self, mock_wait_class, action, mock_element, mock_driver):
        mock_wait = Mock()
        mock_wait.until.return_value = mock_element
        mock_wait_class.return_value = mock_wait
        
        command = FillCommand(
            action=ActionType.SET_VALUE,
            selector="#input",
            value="test value",
        )
        
        result = action.execute(command)
        
        assert result.success == True
        mock_driver.execute_script.assert_called()

