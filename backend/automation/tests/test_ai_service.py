import pytest
from unittest.mock import Mock, patch, MagicMock

from automation.ai_service import (
    AIService,
    AIFormFillingResponse,
    FormFieldMapping,
    NavigationAction,
    SYSTEM_PROMPT,
)


class TestFormFieldMapping:
    def test_to_autofill_command_text(self):
        mapping = FormFieldMapping(
            selector="#firstName",
            selector_type="css",
            action="type_text",
            value="John",
            field_name="First Name",
        )
        
        cmd = mapping.to_autofill_command()
        
        assert cmd["action"] == "type_text"
        assert cmd["selector"] == "#firstName"
        assert cmd["value"] == "John"
    
    def test_to_autofill_command_select(self):
        mapping = FormFieldMapping(
            selector="#country",
            selector_type="css",
            action="select_option",
            value="United States",
            field_name="Country",
        )
        
        cmd = mapping.to_autofill_command()
        
        assert cmd["action"] == "select_option"
        assert cmd["select_by"] == "text"
    
    def test_to_autofill_command_checkbox(self):
        mapping = FormFieldMapping(
            selector="#terms",
            selector_type="css",
            action="check",
            value=True,
            field_name="Terms",
        )
        
        cmd = mapping.to_autofill_command()
        
        assert cmd["action"] == "check"
        assert cmd["checked"] == True


class TestNavigationAction:
    def test_to_autofill_command(self):
        nav = NavigationAction(
            action="click",
            selector="#apply-button",
            description="Click apply",
        )
        
        cmd = nav.to_autofill_command()
        
        assert cmd["action"] == "click"
        assert cmd["selector"] == "#apply-button"
        assert cmd["wait_after_ms"] == 2000


class TestAIFormFillingResponse:
    def test_get_autofill_commands_empty(self):
        response = AIFormFillingResponse()
        
        commands = response.get_autofill_commands()
        
        assert commands == []
    
    def test_get_autofill_commands_with_fields(self):
        response = AIFormFillingResponse(
            field_mappings=[
                FormFieldMapping("#name", "css", "type_text", "John", "Name"),
                FormFieldMapping("#email", "css", "type_text", "john@test.com", "Email"),
            ],
        )
        
        commands = response.get_autofill_commands()
        
        assert len(commands) == 2
    
    def test_get_autofill_commands_with_navigation(self):
        response = AIFormFillingResponse(
            navigation_actions=[
                NavigationAction("click", "#apply-btn"),
            ],
            field_mappings=[
                FormFieldMapping("#name", "css", "type_text", "John", "Name"),
            ],
        )
        
        commands = response.get_autofill_commands()
        
        assert len(commands) == 2
        assert commands[0]["selector"] == "#apply-btn"


class TestAIService:
    def test_init_without_key(self):
        with patch('automation.ai_service.settings') as mock_settings:
            mock_settings.openai_api_key = ""
            
            service = AIService()
            
            assert service.client is None
    
    def test_init_with_key(self):
        with patch('automation.ai_service.openai.OpenAI') as mock_openai:
            service = AIService(api_key="test-key")
            
            assert service.api_key == "test-key"
            mock_openai.assert_called_once_with(api_key="test-key")
    
    def test_build_user_prompt(self):
        with patch('automation.ai_service.openai.OpenAI'):
            service = AIService(api_key="test-key")
        
        page_content = {
            "url": "https://example.com/apply",
            "title": "Job Application",
            "inputs": [
                {"tag": "input", "id": "firstName", "name": "firstName", "type": "text", "label": "First Name"},
            ],
            "buttons": [
                {"id": "submit", "text": "Submit"},
            ],
        }
        
        profile_data = {
            "first_name": "John",
            "last_name": "Doe",
            "email": "john@example.com",
        }
        
        prompt = service._build_user_prompt(page_content, profile_data)
        
        assert "https://example.com/apply" in prompt
        assert "firstName" in prompt
        assert "John" in prompt
        assert "john@example.com" in prompt
    
    def test_parse_response_valid_json(self):
        with patch('automation.ai_service.openai.OpenAI'):
            service = AIService(api_key="test-key")
        
        response_json = """
        {
            "is_form_page": true,
            "needs_navigation": false,
            "page_type": "form",
            "confidence": 0.9,
            "field_mappings": [
                {
                    "field_name": "First Name",
                    "selector": "#firstName",
                    "selector_type": "css",
                    "action": "type_text",
                    "value": "John",
                    "confidence": 1.0
                }
            ],
            "navigation_actions": [],
            "unmapped_fields": []
        }
        """
        
        result = service._parse_response(response_json)
        
        assert result.is_form_page == True
        assert result.confidence == 0.9
        assert len(result.field_mappings) == 1
        assert result.field_mappings[0].value == "John"
    
    def test_parse_response_with_markdown(self):
        with patch('automation.ai_service.openai.OpenAI'):
            service = AIService(api_key="test-key")
        
        response_json = """```json
        {
            "is_form_page": true,
            "needs_navigation": false,
            "page_type": "form",
            "confidence": 0.85
        }
        ```"""
        
        result = service._parse_response(response_json)
        
        assert result.is_form_page == True
        assert result.confidence == 0.85
    
    def test_parse_response_invalid_json(self):
        with patch('automation.ai_service.openai.OpenAI'):
            service = AIService(api_key="test-key")
        
        result = service._parse_response("invalid json {{{")
        
        assert result.is_form_page == False
        assert result.confidence == 0.0


class TestAIServiceIntegration:
    @patch('automation.ai_service.openai.OpenAI')
    def test_analyze_and_generate_commands_sync(self, mock_openai_class):
        mock_client = Mock()
        mock_openai_class.return_value = mock_client
        
        mock_response = Mock()
        mock_response.choices = [Mock()]
        mock_response.choices[0].message.content = """
        {
            "is_form_page": true,
            "needs_navigation": false,
            "page_type": "form",
            "confidence": 0.95,
            "field_mappings": [
                {"field_name": "Email", "selector": "#email", "selector_type": "css", "action": "type_text", "value": "test@example.com"}
            ]
        }
        """
        mock_client.chat.completions.create.return_value = mock_response
        
        service = AIService(api_key="test-key")
        
        result = service.analyze_and_generate_commands_sync(
            {"url": "https://test.com", "inputs": [], "buttons": []},
            {"email": "test@example.com"},
        )
        
        assert result.is_form_page == True
        assert len(result.field_mappings) == 1

