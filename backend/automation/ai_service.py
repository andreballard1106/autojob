import json
import logging
import re
import sys
import traceback
from typing import Any, Dict, List, Optional
from dataclasses import dataclass, field

import openai

from app.config import settings

logger = logging.getLogger(__name__)


def _log_error(message: str, exc: Exception = None):
    """Log error to console with traceback."""
    print(f"[AI SERVICE ERROR] {message}", flush=True)
    if exc:
        print(f"[AI SERVICE ERROR] Exception: {exc}", flush=True)
        traceback.print_exc()
    sys.stdout.flush()


@dataclass
class AutofillCommand:
    """Command that matches the autofill framework FillCommand input format."""
    action: str
    selector: str
    selector_type: str = "css"
    value: Any = None
    select_by: str = "text"
    checked: bool = True
    file_path: Optional[str] = None
    clear_first: bool = True
    wait_after_ms: int = 100
    field_name: str = ""
    confidence: float = 1.0
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dict format for AutofillEngine.execute()"""
        cmd = {
            "action": self.action,
            "selector": self.selector,
            "selector_type": self.selector_type,
        }
        
        if self.action in ["type_text", "type_number", "enter_date"]:
            cmd["value"] = self.value
            cmd["clear_first"] = self.clear_first
        elif self.action == "select_option":
            cmd["value"] = self.value
            cmd["select_by"] = self.select_by
        elif self.action == "check":
            cmd["checked"] = self.checked
        elif self.action == "select_radio":
            cmd["value"] = self.value
        elif self.action == "upload_file":
            cmd["file_path"] = self.file_path
        elif self.action == "click":
            pass
        
        if self.wait_after_ms > 0:
            cmd["wait_after_ms"] = self.wait_after_ms
        
        return cmd


@dataclass
class NavigationButton:
    """Button for navigation (Next/Continue/Submit)."""
    selector: str
    selector_type: str = "css"
    text: str = ""
    button_type: str = "next"
    
    def to_click_command(self) -> Dict[str, Any]:
        return {
            "action": "click",
            "selector": self.selector,
            "selector_type": self.selector_type,
            "wait_after_ms": 2000,
        }


@dataclass
class AIAnalysisResult:
    """Result from OpenAI analysis of job application page."""
    is_form_page: bool = False
    page_type: str = "unknown"
    confidence: float = 0.0
    
    autofill_commands: List[AutofillCommand] = field(default_factory=list)
    
    next_button: Optional[NavigationButton] = None
    submit_button: Optional[NavigationButton] = None
    
    needs_navigation: bool = False
    navigation_commands: List[AutofillCommand] = field(default_factory=list)
    
    unmapped_fields: List[str] = field(default_factory=list)
    error: Optional[str] = None
    
    def get_all_commands(self) -> List[Dict[str, Any]]:
        """Get all autofill commands as dicts."""
        return [cmd.to_dict() for cmd in self.autofill_commands]
    
    def has_next_button(self) -> bool:
        return self.next_button is not None
    
    def has_submit_button(self) -> bool:
        return self.submit_button is not None


SYSTEM_PROMPT = """You are an AI that analyzes job application web pages and generates autofill commands.

Your task:
1. Analyze the page inputs and buttons
2. Match inputs to user profile data
3. Generate EXACT autofill commands for a Selenium-based framework
4. Identify Next/Continue and Submit buttons

=== AUTOFILL COMMAND FORMAT ===

Each command MUST have this structure:
{
    "action": "ACTION_TYPE",
    "selector": "CSS_SELECTOR",
    "selector_type": "css",
    "value": "value_to_fill",
    "field_name": "Human label",
    "confidence": 0.95
}

=== SUPPORTED ACTIONS ===

1. type_text - Text inputs, email, textarea
   Required: selector, value
   
2. type_number - Number inputs  
   Required: selector, value (as number)

3. select_option - Dropdown <select> elements
   Required: selector, value (the visible option text)
   Extra: "select_by": "text" (always use text, not value)

4. check - Checkbox inputs
   Required: selector
   Extra: "checked": true or false

5. select_radio - Radio button selection
   Required: selector (for the specific radio to select), value

6. enter_date - Date inputs
   Required: selector, value (format: "YYYY-MM-DD")

7. click - Click a button/link (for navigation)
   Required: selector

=== SELECTOR RULES ===

Use CSS selectors. Priority:
1. ID: "#elementId"
2. Name: "[name='fieldName']" 
3. Data attrs: "[data-automation-id='value']", "[data-testid='value']"
4. Type+Name: "input[type='email'][name='email']"
5. Aria: "[aria-label='Email']"

selector_type is always "css" unless absolutely necessary to use "xpath".

=== OUTPUT JSON FORMAT ===

{
    "is_form_page": true,
    "page_type": "application_form",
    "confidence": 0.9,
    "needs_navigation": false,
    
    "autofill_commands": [
        {
            "action": "type_text",
            "selector": "#firstName",
            "selector_type": "css",
            "value": "John",
            "field_name": "First Name",
            "confidence": 1.0
        },
        {
            "action": "select_option",
            "selector": "#country",
            "selector_type": "css", 
            "value": "United States",
            "select_by": "text",
            "field_name": "Country",
            "confidence": 0.95
        },
        {
            "action": "check",
            "selector": "#agreeTerms",
            "selector_type": "css",
            "checked": true,
            "field_name": "Terms Agreement",
            "confidence": 1.0
        }
    ],
    
    "next_button": {
        "selector": "button[data-automation-id='bottom-navigation-next-button']",
        "selector_type": "css",
        "text": "Continue"
    },
    
    "submit_button": null,
    
    "navigation_commands": [],
    
    "unmapped_fields": ["Resume Upload", "Cover Letter", "How did you hear about us?"]
}

=== PAGE TYPES ===

- "application_form" - Has form fields to fill
- "job_listing" - Job description, needs "Apply" button click
- "login_page" - Login required
- "confirmation" - Application submitted
- "multi_step_form" - Part of multi-page application

=== CRITICAL RULES ===

1. ONLY fill fields you can CONFIDENTLY match to profile data
2. Use the EXACT selector that will find the element
3. For dropdowns, value is the VISIBLE TEXT of the option
4. Always identify Next/Continue buttons as next_button
5. Always identify Submit/Apply buttons as submit_button  
6. File upload fields go in unmapped_fields (cannot auto-fill)
7. Return VALID JSON only - no markdown, no comments
8. If page needs login or navigation first, set needs_navigation=true
9. Set confidence based on how sure you are about the match"""


class AIService:
    def __init__(self, api_key: str = None, model: str = None):
        self.api_key = api_key or settings.openai_api_key
        self.model = model or "gpt-4o"
        self.client = None
        
        if self.api_key:
            self.client = openai.OpenAI(api_key=self.api_key)
    
    def _build_prompt(
        self,
        page_content: Dict[str, Any],
        profile_data: Dict[str, Any],
    ) -> str:
        """Build the prompt for OpenAI with page content and profile data."""
        lines = []
        
        lines.append("=== PAGE TO ANALYZE ===")
        lines.append(f"URL: {page_content.get('url', 'unknown')}")
        lines.append(f"Title: {page_content.get('title', 'unknown')}")
        
        lines.append("\n=== FORM INPUTS FOUND ===")
        inputs = page_content.get("inputs", [])
        if not inputs:
            lines.append("(No form inputs found)")
        else:
            for idx, inp in enumerate(inputs[:60]):
                parts = [f"{idx+1}."]
                
                tag = inp.get('tag', 'input')
                inp_type = inp.get('type', '')
                parts.append(f"<{tag}" + (f" type='{inp_type}'" if inp_type else "") + ">")
                
                if inp.get('id'):
                    parts.append(f"id='{inp['id']}'")
                if inp.get('name'):
                    parts.append(f"name='{inp['name']}'")
                if inp.get('label'):
                    parts.append(f"label='{inp['label']}'")
                if inp.get('placeholder'):
                    parts.append(f"placeholder='{inp['placeholder']}'")
                if inp.get('required'):
                    parts.append("[REQUIRED]")
                if inp.get('aria-label'):
                    parts.append(f"aria-label='{inp['aria-label']}'")
                
                if inp.get('options'):
                    opts = [str(o.get('text', o.get('value', '')))[:25] for o in inp['options'][:6]]
                    parts.append(f"options={opts}")
                
                lines.append(" ".join(parts))
        
        lines.append("\n=== BUTTONS FOUND ===")
        buttons = page_content.get("buttons", [])
        if not buttons:
            lines.append("(No buttons found)")
        else:
            for idx, btn in enumerate(buttons[:30]):
                parts = [f"{idx+1}. BUTTON"]
                if btn.get('id'):
                    parts.append(f"id='{btn['id']}'")
                if btn.get('text'):
                    parts.append(f"text='{btn['text']}'")
                if btn.get('type'):
                    parts.append(f"type='{btn['type']}'")
                if btn.get('data-automation-id'):
                    parts.append(f"data-automation-id='{btn['data-automation-id']}'")
                lines.append(" ".join(parts))
        
        lines.append("\n=== USER PROFILE DATA ===")
        lines.append(f"First Name: {profile_data.get('first_name', '')}")
        lines.append(f"Middle Name: {profile_data.get('middle_name', '')}")
        lines.append(f"Last Name: {profile_data.get('last_name', '')}")
        lines.append(f"Email: {profile_data.get('email', '')}")
        lines.append(f"Phone: {profile_data.get('phone', '')}")
        
        if profile_data.get('address_1'):
            lines.append(f"Address Line 1: {profile_data['address_1']}")
        if profile_data.get('address_2'):
            lines.append(f"Address Line 2: {profile_data['address_2']}")
        if profile_data.get('city'):
            lines.append(f"City: {profile_data['city']}")
        if profile_data.get('state'):
            lines.append(f"State/Province: {profile_data['state']}")
        if profile_data.get('zip_code'):
            lines.append(f"ZIP/Postal Code: {profile_data['zip_code']}")
        if profile_data.get('country'):
            lines.append(f"Country: {profile_data['country']}")
        
        if profile_data.get('linkedin_url'):
            lines.append(f"LinkedIn URL: {profile_data['linkedin_url']}")
        if profile_data.get('github_url'):
            lines.append(f"GitHub URL: {profile_data['github_url']}")
        if profile_data.get('portfolio_url'):
            lines.append(f"Portfolio URL: {profile_data['portfolio_url']}")
        
        work_exp = profile_data.get('work_experience', [])
        if work_exp:
            lines.append("\nWork Experience:")
            for exp in work_exp[:3]:
                title = exp.get('job_title', exp.get('title', ''))
                company = exp.get('company_name', exp.get('company', ''))
                start = exp.get('start_date', '')
                end = exp.get('end_date', 'Present')
                lines.append(f"  - {title} at {company} ({start} - {end})")
        
        education = profile_data.get('education', [])
        if education:
            lines.append("\nEducation:")
            for edu in education[:2]:
                degree = edu.get('degree', '')
                major = edu.get('major', edu.get('field', ''))
                school = edu.get('university_name', edu.get('school', ''))
                lines.append(f"  - {degree} in {major} from {school}")
        
        skills = profile_data.get('skills', [])
        if skills:
            lines.append(f"\nSkills: {', '.join(skills[:15])}")
        
        lines.append("\n=== TASK ===")
        lines.append("Generate autofill commands to fill this form with the profile data.")
        lines.append("Identify the Next/Continue button and Submit button if present.")
        lines.append("Return valid JSON matching the required format.")
        
        return "\n".join(lines)
    
    def _parse_response(self, content: str) -> AIAnalysisResult:
        """Parse OpenAI response into AIAnalysisResult."""
        content = content.strip()
        
        if content.startswith("```"):
            content = re.sub(r'^```(?:json)?\s*', '', content)
            content = re.sub(r'\s*```$', '', content)
        
        try:
            data = json.loads(content)
        except json.JSONDecodeError as e:
            print(f"  [AI-PARSE] JSON parse error: {e}")
            print(f"  [AI-PARSE] Content preview: {content[:300]}...")
            return AIAnalysisResult(
                is_form_page=False,
                error=f"Failed to parse AI response: {e}",
            )
        
        result = AIAnalysisResult(
            is_form_page=data.get("is_form_page", False),
            page_type=data.get("page_type", "unknown"),
            confidence=data.get("confidence", 0.0),
            needs_navigation=data.get("needs_navigation", False),
            unmapped_fields=data.get("unmapped_fields", []),
        )
        
        for cmd_data in data.get("autofill_commands", []):
            cmd = AutofillCommand(
                action=cmd_data.get("action", "type_text"),
                selector=cmd_data.get("selector", ""),
                selector_type=cmd_data.get("selector_type", "css"),
                value=cmd_data.get("value"),
                select_by=cmd_data.get("select_by", "text"),
                checked=cmd_data.get("checked", True),
                file_path=cmd_data.get("file_path"),
                field_name=cmd_data.get("field_name", ""),
                confidence=cmd_data.get("confidence", 1.0),
            )
            result.autofill_commands.append(cmd)
        
        if data.get("next_button"):
            nb = data["next_button"]
            result.next_button = NavigationButton(
                selector=nb.get("selector", ""),
                selector_type=nb.get("selector_type", "css"),
                text=nb.get("text", ""),
                button_type="next",
            )
        
        if data.get("submit_button"):
            sb = data["submit_button"]
            result.submit_button = NavigationButton(
                selector=sb.get("selector", ""),
                selector_type=sb.get("selector_type", "css"),
                text=sb.get("text", ""),
                button_type="submit",
            )
        
        for nav_data in data.get("navigation_commands", []):
            cmd = AutofillCommand(
                action=nav_data.get("action", "click"),
                selector=nav_data.get("selector", ""),
                selector_type=nav_data.get("selector_type", "css"),
                field_name=nav_data.get("description", ""),
            )
            result.navigation_commands.append(cmd)
        
        return result
    
    def analyze_page(
        self,
        page_content: Dict[str, Any],
        profile_data: Dict[str, Any],
    ) -> AIAnalysisResult:
        """
        Analyze a job application page and generate autofill commands.
        
        Args:
            page_content: Extracted page content (url, title, inputs, buttons)
            profile_data: User profile data to use for filling
            
        Returns:
            AIAnalysisResult with autofill commands and navigation info
        """
        if not self.client:
            print("  [AI] ERROR: OpenAI client not initialized")
            return AIAnalysisResult(error="OpenAI client not initialized")
        
        prompt = self._build_prompt(page_content, profile_data)
        
        print(f"  [AI] Sending to OpenAI ({self.model})...")
        print(f"  [AI] Page has {len(page_content.get('inputs', []))} inputs, "
              f"{len(page_content.get('buttons', []))} buttons")
        print(f"  [AI] Profile: {profile_data.get('first_name', '?')} {profile_data.get('last_name', '?')}")
        
        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": SYSTEM_PROMPT},
                    {"role": "user", "content": prompt},
                ],
                temperature=0.1,
                max_tokens=4000,
            )
            
            content = response.choices[0].message.content
            print(f"  [AI] Response received ({len(content)} chars)")
            
            result = self._parse_response(content)
            
            print(f"  [AI] Parsed result:")
            print(f"       - is_form_page: {result.is_form_page}")
            print(f"       - page_type: {result.page_type}")
            print(f"       - autofill_commands: {len(result.autofill_commands)}")
            print(f"       - next_button: {result.next_button.selector if result.next_button else 'None'}")
            print(f"       - submit_button: {result.submit_button.selector if result.submit_button else 'None'}")
            print(f"       - unmapped_fields: {len(result.unmapped_fields)}")
            
            if result.autofill_commands:
                print(f"  [AI] First 3 commands:")
                for cmd in result.autofill_commands[:3]:
                    print(f"       - {cmd.field_name}: {cmd.action} -> {cmd.selector[:40]}")
            
            return result
            
        except Exception as e:
            print(f"  [AI] ERROR: {e}")
            import traceback
            traceback.print_exc()
            return AIAnalysisResult(error=str(e))
    
    def analyze_and_generate_commands_sync(
        self,
        page_content: Dict[str, Any],
        profile_data: Dict[str, Any],
    ) -> "AIFormFillingResponse":
        """
        Legacy method for backward compatibility.
        Converts AIAnalysisResult to AIFormFillingResponse format.
        """
        result = self.analyze_page(page_content, profile_data)
        
        from dataclasses import dataclass as dc
        
        @dc
        class FormFieldMapping:
            selector: str
            selector_type: str
            action: str
            value: Any
            field_name: str
            confidence: float = 1.0
            select_by: str = "text"
            checked: bool = True
            
            def to_autofill_command(self) -> Dict[str, Any]:
                cmd = {
                    "action": self.action,
                    "selector": self.selector,
                    "selector_type": self.selector_type,
                    "value": self.value,
                }
                if self.action == "select_option":
                    cmd["select_by"] = self.select_by
                elif self.action == "check":
                    cmd["checked"] = self.checked
                return cmd
        
        @dc  
        class NavigationAction:
            action: str
            selector: str
            selector_type: str = "css"
            description: str = ""
            wait_after_ms: int = 2000
            
            def to_autofill_command(self) -> Dict[str, Any]:
                return {
                    "action": self.action,
                    "selector": self.selector,
                    "selector_type": self.selector_type,
                    "wait_after_ms": self.wait_after_ms,
                }
        
        @dc
        class AIFormFillingResponse:
            is_form_page: bool = True
            needs_navigation: bool = False
            navigation_actions: List = None
            field_mappings: List = None
            unmapped_fields: List[str] = None
            page_type: str = "unknown"
            confidence: float = 0.0
            next_button: Optional[Dict] = None
            submit_button: Optional[Dict] = None
            
            def __post_init__(self):
                self.navigation_actions = self.navigation_actions or []
                self.field_mappings = self.field_mappings or []
                self.unmapped_fields = self.unmapped_fields or []
        
        field_mappings = []
        for cmd in result.autofill_commands:
            field_mappings.append(FormFieldMapping(
                selector=cmd.selector,
                selector_type=cmd.selector_type,
                action=cmd.action,
                value=cmd.value,
                field_name=cmd.field_name,
                confidence=cmd.confidence,
                select_by=cmd.select_by,
                checked=cmd.checked,
            ))
        
        nav_actions = []
        for cmd in result.navigation_commands:
            nav_actions.append(NavigationAction(
                action=cmd.action,
                selector=cmd.selector,
                selector_type=cmd.selector_type,
                description=cmd.field_name,
            ))
        
        response = AIFormFillingResponse(
            is_form_page=result.is_form_page,
            needs_navigation=result.needs_navigation,
            navigation_actions=nav_actions,
            field_mappings=field_mappings,
            unmapped_fields=result.unmapped_fields,
            page_type=result.page_type,
            confidence=result.confidence,
        )
        
        if result.next_button:
            response.next_button = {
                "selector": result.next_button.selector,
                "selector_type": result.next_button.selector_type,
                "text": result.next_button.text,
            }
        
        if result.submit_button:
            response.submit_button = {
                "selector": result.submit_button.selector,
                "selector_type": result.submit_button.selector_type,
                "text": result.submit_button.text,
            }
        
        return response
    
    async def analyze_and_generate_commands(
        self,
        page_content: Dict[str, Any],
        profile_data: Dict[str, Any],
    ):
        """Async version of analyze_and_generate_commands_sync."""
        return self.analyze_and_generate_commands_sync(page_content, profile_data)
