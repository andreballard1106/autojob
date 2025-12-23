import pytest
from autofill.models import (
    ActionType,
    SelectorType,
    SelectBy,
    WaitCondition,
    FillCommand,
    FillResult,
)


class TestActionType:
    def test_all_action_types_exist(self):
        expected_actions = [
            "type_text", "type_number", "select_option", "select_multiple",
            "select_autocomplete", "check", "select_radio", "upload_file",
            "enter_date", "click", "double_click", "right_click", "hover",
            "clear", "focus", "blur", "scroll_to", "scroll_by", "wait",
            "press_key", "drag_drop", "set_value", "execute_js",
            "switch_iframe", "switch_default",
        ]
        for action in expected_actions:
            assert hasattr(ActionType, action.upper())
    
    def test_action_type_values(self):
        assert ActionType.TYPE_TEXT.value == "type_text"
        assert ActionType.CLICK.value == "click"
        assert ActionType.SELECT_OPTION.value == "select_option"


class TestSelectorType:
    def test_selector_types(self):
        assert SelectorType.CSS.value == "css"
        assert SelectorType.XPATH.value == "xpath"
        assert SelectorType.ID.value == "id"
        assert SelectorType.NAME.value == "name"


class TestSelectBy:
    def test_select_by_options(self):
        assert SelectBy.VALUE.value == "value"
        assert SelectBy.TEXT.value == "text"
        assert SelectBy.INDEX.value == "index"


class TestWaitCondition:
    def test_wait_conditions(self):
        assert WaitCondition.VISIBLE.value == "visible"
        assert WaitCondition.HIDDEN.value == "hidden"
        assert WaitCondition.CLICKABLE.value == "clickable"
        assert WaitCondition.PRESENT.value == "present"


class TestFillCommand:
    def test_from_dict_basic(self):
        data = {
            "action": "type_text",
            "selector": "#email",
            "value": "test@example.com",
        }
        command = FillCommand.from_dict(data)
        
        assert command.action == ActionType.TYPE_TEXT
        assert command.selector == "#email"
        assert command.value == "test@example.com"
        assert command.selector_type == SelectorType.CSS
        assert command.clear_first == True
    
    def test_from_dict_with_options(self):
        data = {
            "action": "select_option",
            "selector": "#country",
            "value": "US",
            "select_by": "value",
            "selector_type": "css",
        }
        command = FillCommand.from_dict(data)
        
        assert command.action == ActionType.SELECT_OPTION
        assert command.select_by == SelectBy.VALUE
        assert command.selector_type == SelectorType.CSS
    
    def test_from_dict_checkbox(self):
        data = {
            "action": "check",
            "selector": "#agree",
            "checked": False,
        }
        command = FillCommand.from_dict(data)
        
        assert command.action == ActionType.CHECK
        assert command.checked == False
    
    def test_from_dict_file_upload(self):
        data = {
            "action": "upload_file",
            "selector": "#resume",
            "file_path": "/path/to/resume.pdf",
        }
        command = FillCommand.from_dict(data)
        
        assert command.action == ActionType.UPLOAD_FILE
        assert command.file_path == "/path/to/resume.pdf"
    
    def test_from_dict_wait(self):
        data = {
            "action": "wait",
            "time_ms": 2000,
        }
        command = FillCommand.from_dict(data)
        
        assert command.action == ActionType.WAIT
        assert command.time_ms == 2000
    
    def test_from_dict_wait_condition(self):
        data = {
            "action": "wait",
            "selector": "#loading",
            "condition": "hidden",
            "timeout_ms": 5000,
        }
        command = FillCommand.from_dict(data)
        
        assert command.condition == WaitCondition.HIDDEN
        assert command.timeout_ms == 5000
    
    def test_from_dict_date(self):
        data = {
            "action": "enter_date",
            "selector": "#start_date",
            "value": "2024-01-15",
            "date_format": "MM/DD/YYYY",
        }
        command = FillCommand.from_dict(data)
        
        assert command.action == ActionType.ENTER_DATE
        assert command.date_format == "MM/DD/YYYY"
    
    def test_from_dict_radio(self):
        data = {
            "action": "select_radio",
            "name": "gender",
            "value": "male",
        }
        command = FillCommand.from_dict(data)
        
        assert command.action == ActionType.SELECT_RADIO
        assert command.name == "gender"
        assert command.value == "male"


class TestFillResult:
    def test_success_result(self):
        result = FillResult(
            success=True,
            action=ActionType.TYPE_TEXT,
            selector="#email",
            value_used="test@example.com",
            duration_ms=150,
        )
        
        assert result.success == True
        assert result.element_found == True
        assert result.error is None
    
    def test_failure_result(self):
        result = FillResult(
            success=False,
            action=ActionType.CLICK,
            selector="#submit",
            element_found=False,
            error="Element not found",
            duration_ms=5000,
        )
        
        assert result.success == False
        assert result.element_found == False
        assert "Element not found" in result.error
    
    def test_to_dict(self):
        result = FillResult(
            success=True,
            action=ActionType.TYPE_TEXT,
            selector="#email",
            value_used="test@example.com",
            duration_ms=150,
        )
        
        d = result.to_dict()
        
        assert d["success"] == True
        assert d["action"] == "type_text"
        assert d["selector"] == "#email"
        assert d["value_used"] == "test@example.com"
        assert d["duration_ms"] == 150

