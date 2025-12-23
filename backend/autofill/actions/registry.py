from typing import Dict, Type

from selenium.webdriver.remote.webdriver import WebDriver

from autofill.models import ActionType
from autofill.actions.base import BaseAction
from autofill.actions.text import TypeTextAction, TypeNumberAction
from autofill.actions.select import SelectOptionAction, SelectMultipleAction, SelectAutocompleteAction
from autofill.actions.checkbox import CheckAction, SelectRadioAction
from autofill.actions.file import UploadFileAction
from autofill.actions.date import EnterDateAction
from autofill.actions.click import ClickAction, DoubleClickAction, RightClickAction
from autofill.actions.utility import (
    ClearAction,
    FocusAction,
    BlurAction,
    ScrollToAction,
    ScrollByAction,
    WaitAction,
    PressKeyAction,
    HoverAction,
    SetValueAction,
    ExecuteJsAction,
    SwitchIframeAction,
    SwitchDefaultAction,
    DragDropAction,
)


class ActionRegistry:
    _action_classes: Dict[ActionType, Type[BaseAction]] = {
        ActionType.TYPE_TEXT: TypeTextAction,
        ActionType.TYPE_NUMBER: TypeNumberAction,
        ActionType.SELECT_OPTION: SelectOptionAction,
        ActionType.SELECT_MULTIPLE: SelectMultipleAction,
        ActionType.SELECT_AUTOCOMPLETE: SelectAutocompleteAction,
        ActionType.CHECK: CheckAction,
        ActionType.SELECT_RADIO: SelectRadioAction,
        ActionType.UPLOAD_FILE: UploadFileAction,
        ActionType.ENTER_DATE: EnterDateAction,
        ActionType.CLICK: ClickAction,
        ActionType.DOUBLE_CLICK: DoubleClickAction,
        ActionType.RIGHT_CLICK: RightClickAction,
        ActionType.HOVER: HoverAction,
        ActionType.CLEAR: ClearAction,
        ActionType.FOCUS: FocusAction,
        ActionType.BLUR: BlurAction,
        ActionType.SCROLL_TO: ScrollToAction,
        ActionType.SCROLL_BY: ScrollByAction,
        ActionType.WAIT: WaitAction,
        ActionType.PRESS_KEY: PressKeyAction,
        ActionType.DRAG_DROP: DragDropAction,
        ActionType.SET_VALUE: SetValueAction,
        ActionType.EXECUTE_JS: ExecuteJsAction,
        ActionType.SWITCH_IFRAME: SwitchIframeAction,
        ActionType.SWITCH_DEFAULT: SwitchDefaultAction,
    }
    
    def __init__(self, driver: WebDriver):
        self.driver = driver
        self._instances: Dict[ActionType, BaseAction] = {}
    
    def get_action(self, action_type: ActionType) -> BaseAction:
        if action_type not in self._instances:
            action_class = self._action_classes.get(action_type)
            if not action_class:
                raise ValueError(f"Unknown action type: {action_type}")
            self._instances[action_type] = action_class(self.driver)
        return self._instances[action_type]
    
    @classmethod
    def register_action(cls, action_type: ActionType, action_class: Type[BaseAction]) -> None:
        cls._action_classes[action_type] = action_class
    
    @classmethod
    def get_supported_actions(cls) -> list:
        return list(cls._action_classes.keys())
