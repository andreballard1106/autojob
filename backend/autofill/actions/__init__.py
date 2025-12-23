from autofill.actions.base import BaseAction
from autofill.actions.text import TypeTextAction, TypeNumberAction
from autofill.actions.select import SelectOptionAction, SelectMultipleAction, SelectAutocompleteAction
from autofill.actions.checkbox import CheckAction, SelectRadioAction
from autofill.actions.file import UploadFileAction
from autofill.actions.date import EnterDateAction
from autofill.actions.click import ClickAction
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
from autofill.actions.registry import ActionRegistry

__all__ = [
    "BaseAction",
    "TypeTextAction",
    "TypeNumberAction",
    "SelectOptionAction",
    "SelectMultipleAction",
    "SelectAutocompleteAction",
    "CheckAction",
    "SelectRadioAction",
    "UploadFileAction",
    "EnterDateAction",
    "ClickAction",
    "ClearAction",
    "FocusAction",
    "BlurAction",
    "ScrollToAction",
    "ScrollByAction",
    "WaitAction",
    "PressKeyAction",
    "HoverAction",
    "SetValueAction",
    "ExecuteJsAction",
    "SwitchIframeAction",
    "SwitchDefaultAction",
    "DragDropAction",
    "ActionRegistry",
]
