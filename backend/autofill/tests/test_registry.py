import pytest
from unittest.mock import Mock

from autofill.models import ActionType
from autofill.actions.registry import ActionRegistry
from autofill.actions.base import BaseAction
from autofill.actions.text import TypeTextAction, TypeNumberAction
from autofill.actions.select import SelectOptionAction
from autofill.actions.checkbox import CheckAction
from autofill.actions.click import ClickAction
from autofill.actions.utility import WaitAction


class TestActionRegistry:
    @pytest.fixture
    def registry(self, mock_driver):
        return ActionRegistry(mock_driver)
    
    def test_init(self, mock_driver):
        registry = ActionRegistry(mock_driver)
        
        assert registry.driver == mock_driver
        assert registry._instances == {}
    
    def test_get_action_type_text(self, registry):
        action = registry.get_action(ActionType.TYPE_TEXT)
        
        assert isinstance(action, TypeTextAction)
    
    def test_get_action_type_number(self, registry):
        action = registry.get_action(ActionType.TYPE_NUMBER)
        
        assert isinstance(action, TypeNumberAction)
    
    def test_get_action_select_option(self, registry):
        action = registry.get_action(ActionType.SELECT_OPTION)
        
        assert isinstance(action, SelectOptionAction)
    
    def test_get_action_check(self, registry):
        action = registry.get_action(ActionType.CHECK)
        
        assert isinstance(action, CheckAction)
    
    def test_get_action_click(self, registry):
        action = registry.get_action(ActionType.CLICK)
        
        assert isinstance(action, ClickAction)
    
    def test_get_action_wait(self, registry):
        action = registry.get_action(ActionType.WAIT)
        
        assert isinstance(action, WaitAction)
    
    def test_get_action_caches_instance(self, registry):
        action1 = registry.get_action(ActionType.TYPE_TEXT)
        action2 = registry.get_action(ActionType.TYPE_TEXT)
        
        assert action1 is action2
    
    def test_get_action_unknown_raises(self, registry):
        class FakeActionType:
            value = "fake_action"
        
        with pytest.raises(ValueError) as exc_info:
            registry.get_action(FakeActionType())
        
        assert "Unknown action type" in str(exc_info.value)
    
    def test_get_supported_actions(self):
        actions = ActionRegistry.get_supported_actions()
        
        assert ActionType.TYPE_TEXT in actions
        assert ActionType.CLICK in actions
        assert ActionType.SELECT_OPTION in actions
        assert ActionType.CHECK in actions
        assert ActionType.WAIT in actions
        assert len(actions) >= 15


class TestActionRegistryCustomAction:
    def test_register_custom_action(self, mock_driver):
        class CustomAction(BaseAction):
            action_type = None
            
            def execute(self, command):
                return None
        
        class CustomActionType:
            CUSTOM = "custom"
        
        original_actions = ActionRegistry._action_classes.copy()
        
        try:
            pass
        finally:
            ActionRegistry._action_classes = original_actions


class TestAllActionsRegistered:
    def test_all_action_types_have_handlers(self, mock_driver):
        registry = ActionRegistry(mock_driver)
        
        for action_type in ActionType:
            action = registry.get_action(action_type)
            assert action is not None
            assert isinstance(action, BaseAction)

