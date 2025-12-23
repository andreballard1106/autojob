from enum import Enum
from dataclasses import dataclass, field
from typing import Any, Optional, List, Dict


class ActionType(str, Enum):
    TYPE_TEXT = "type_text"
    TYPE_NUMBER = "type_number"
    SELECT_OPTION = "select_option"
    SELECT_MULTIPLE = "select_multiple"
    SELECT_AUTOCOMPLETE = "select_autocomplete"
    CHECK = "check"
    SELECT_RADIO = "select_radio"
    UPLOAD_FILE = "upload_file"
    ENTER_DATE = "enter_date"
    CLICK = "click"
    DOUBLE_CLICK = "double_click"
    RIGHT_CLICK = "right_click"
    HOVER = "hover"
    CLEAR = "clear"
    FOCUS = "focus"
    BLUR = "blur"
    SCROLL_TO = "scroll_to"
    SCROLL_BY = "scroll_by"
    WAIT = "wait"
    PRESS_KEY = "press_key"
    DRAG_DROP = "drag_drop"
    SET_VALUE = "set_value"
    EXECUTE_JS = "execute_js"
    SWITCH_IFRAME = "switch_iframe"
    SWITCH_DEFAULT = "switch_default"


class SelectorType(str, Enum):
    CSS = "css"
    XPATH = "xpath"
    ID = "id"
    NAME = "name"


class SelectBy(str, Enum):
    VALUE = "value"
    TEXT = "text"
    INDEX = "index"


class WaitCondition(str, Enum):
    VISIBLE = "visible"
    HIDDEN = "hidden"
    CLICKABLE = "clickable"
    PRESENT = "present"


@dataclass
class FillCommand:
    action: ActionType
    selector: Optional[str] = None
    selector_type: SelectorType = SelectorType.CSS
    value: Any = None
    clear_first: bool = True
    delay_ms: int = 0
    select_by: SelectBy = SelectBy.VALUE
    checked: bool = True
    file_path: Optional[str] = None
    file_paths: Optional[List[str]] = None
    date_format: str = "YYYY-MM-DD"
    wait_after_ms: int = 0
    double_click: bool = False
    time_ms: int = 0
    condition: WaitCondition = WaitCondition.VISIBLE
    key: Optional[str] = None
    name: Optional[str] = None
    timeout_ms: int = 10000
    options: Dict[str, Any] = field(default_factory=dict)
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "FillCommand":
        action = data.get("action")
        if isinstance(action, str):
            action = ActionType(action)
        
        selector_type = data.get("selector_type", "css")
        if isinstance(selector_type, str):
            selector_type = SelectorType(selector_type)
        
        select_by = data.get("select_by", "value")
        if isinstance(select_by, str):
            select_by = SelectBy(select_by)
        
        condition = data.get("condition", "visible")
        if isinstance(condition, str):
            condition = WaitCondition(condition)
        
        return cls(
            action=action,
            selector=data.get("selector"),
            selector_type=selector_type,
            value=data.get("value"),
            clear_first=data.get("clear_first", True),
            delay_ms=data.get("delay_ms", 0),
            select_by=select_by,
            checked=data.get("checked", True),
            file_path=data.get("file_path"),
            file_paths=data.get("file_paths"),
            date_format=data.get("date_format", "YYYY-MM-DD"),
            wait_after_ms=data.get("wait_after_ms", 0),
            double_click=data.get("double_click", False),
            time_ms=data.get("time_ms", 0),
            condition=condition,
            key=data.get("key"),
            name=data.get("name"),
            timeout_ms=data.get("timeout_ms", 10000),
            options=data.get("options", {}),
        )


@dataclass
class FillResult:
    success: bool
    action: ActionType
    selector: Optional[str] = None
    value_used: Any = None
    element_found: bool = True
    error: Optional[str] = None
    duration_ms: int = 0
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "success": self.success,
            "action": self.action.value if isinstance(self.action, ActionType) else self.action,
            "selector": self.selector,
            "value_used": self.value_used,
            "element_found": self.element_found,
            "error": self.error,
            "duration_ms": self.duration_ms,
        }

