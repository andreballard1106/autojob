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
    # Platform identification
    platform: str = "unknown"  # workday, greenhouse, lever, workable, etc.
    
    is_form_page: bool = False
    page_type: str = "unknown"
    confidence: float = 0.0
    
    autofill_commands: List[AutofillCommand] = field(default_factory=list)
    
    # Navigation buttons - mutually exclusive purposes:
    # - apply_button: For job listing pages to START the application
    # - next_button: For multi-step forms to go to NEXT step
    # - submit_button: For FINAL submission of completed application
    apply_button: Optional[NavigationButton] = None
    next_button: Optional[NavigationButton] = None
    submit_button: Optional[NavigationButton] = None
    
    needs_navigation: bool = False
    navigation_commands: List[AutofillCommand] = field(default_factory=list)
    
    unmapped_fields: List[str] = field(default_factory=list)
    error: Optional[str] = None
    
    def get_all_commands(self) -> List[Dict[str, Any]]:
        """Get all autofill commands as dicts."""
        return [cmd.to_dict() for cmd in self.autofill_commands]
    
    def has_apply_button(self) -> bool:
        return self.apply_button is not None
    
    def has_next_button(self) -> bool:
        return self.next_button is not None
    
    def has_submit_button(self) -> bool:
        return self.submit_button is not None
    
    def get_navigation_button(self) -> Optional[NavigationButton]:
        """Get the most appropriate navigation button for current page state."""
        # Priority: apply_button (start) > next_button (continue) > submit_button (finish)
        if self.apply_button:
            return self.apply_button
        if self.next_button:
            return self.next_button
        if self.submit_button:
            return self.submit_button
        return None


SYSTEM_PROMPT = """You are an AI that analyzes job application web pages and generates autofill commands.

Your task:
1. FIRST determine the page type (job listing, application form, multi-step form, etc.)
2. Analyze the page inputs and buttons
3. Match inputs to user profile data (including file uploads for resume/cover letter)
4. Generate EXACT autofill commands for a Selenium-based framework
5. Identify the appropriate navigation button based on page type

=== PAGE TYPE DETECTION (CRITICAL) ===

FIRST, determine the page type based on these indicators:

1. "job_listing" - A job description page that requires clicking an Apply button to START the application
   Indicators:
   - Job title, company name, job description are prominently displayed
   - Has "Apply", "Apply Now", "Apply for this job", "Start Application" button
   - Few or NO form input fields (maybe just email capture)
   - Page shows job requirements, responsibilities, qualifications
   ACTION: Set is_form_page=false, needs_navigation=true, provide apply_button

2. "application_form" - The ACTUAL job application form with fields to fill
   Indicators:
   - Multiple input fields for personal info (name, email, phone, address)
   - File upload fields for resume/cover letter
   - Work experience, education sections
   - May have "Next", "Continue", "Submit" buttons
   ACTION: Set is_form_page=true, fill autofill_commands, provide next_button or submit_button

3. "multi_step_form" - One page in a multi-page application wizard
   Indicators:
   - Progress indicator showing steps (Step 1 of 5, etc.)
   - "Next", "Continue", "Save and Continue" buttons
   - Form fields for one section (e.g., only personal info, or only work history)
   ACTION: Set is_form_page=true, fill autofill_commands, provide next_button

4. "review_page" - A page to review the application before submission
   Indicators:
   - Shows summary of entered information
   - "Submit", "Submit Application", "Confirm" buttons
   - Usually no editable fields (or minimal)
   ACTION: Set is_form_page=false, provide submit_button

5. "login_page" - Requires login/signup before application
   Indicators:
   - Login/signup form prominently displayed
   - "Sign In", "Create Account", "Register" buttons
   ACTION: Set is_form_page=false, needs_navigation=true, provide login form fields

6. "confirmation" - Application already submitted
   Indicators:
   - "Thank you", "Application Received", "Confirmation" messages
   - No more action required
   ACTION: Set is_form_page=false, needs_navigation=false

=== JOB PLATFORM DETECTION ===

IMPORTANT: Identify the job application platform from URL patterns, page structure, and HTML attributes.

Known platforms and their identifiers:

1. "workday" (Oracle Cloud HCM / Workday)
   - URL contains: myworkdayjobs.com, wd5.myworkdaysite.com, workday.com
   - Has data-automation-id attributes
   - Progressive disclosure forms

2. "greenhouse"
   - URL contains: greenhouse.io, boards.greenhouse.io
   - Job board structure with specific styling
   - Standard application form layout

3. "lever"
   - URL contains: lever.co, jobs.lever.co
   - Clean, minimal design
   - Single-page or simple multi-step forms

4. "workable"
   - URL contains: workable.com, apply.workable.com
   - Standard ATS form structure

5. "smartrecruiters"
   - URL contains: smartrecruiters.com, jobs.smartrecruiters.com
   - Enterprise-style forms

6. "icims"
   - URL contains: icims.com, careers-*.icims.com
   - Complex multi-step wizard

7. "taleo"
   - URL contains: taleo.net, oracle.taleo.net
   - Legacy Oracle system, table-based layouts

8. "successfactors"
   - URL contains: successfactors.com, jobs.sap.com
   - SAP-style forms

9. "jobvite"
   - URL contains: jobvite.com, jobs.jobvite.com
   - Modern application flow

10. "bamboohr"
    - URL contains: bamboohr.com
    - Simple, clean forms

11. "ashbyhq"
    - URL contains: ashbyhq.com, jobs.ashbyhq.com
    - Modern startup-focused ATS

12. "custom" - Company's own application system
    - No recognizable ATS patterns
    - Custom domain without known ATS identifiers

13. "unknown" - Cannot determine platform
    - Use this when platform cannot be identified

Set platform based on URL pattern FIRST, then verify with page structure if unsure.

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

7. upload_file - File input for resume, cover letter, documents
   Required: selector, file_path (the absolute path to the file)
   Use this for input[type='file'] elements
   IMPORTANT: Match resume file inputs to the user's resume_path
   IMPORTANT: Match cover letter file inputs to cover_letter_template_path

8. click - Click a button/link (for navigation)
   Required: selector

=== FILE UPLOAD RULES ===

When you see input[type='file'] or file upload elements:
- For RESUME uploads: Use "upload_file" action with the user's resume_path
- For COVER LETTER uploads: Use "upload_file" action with the user's cover_letter_template_path
- If the file path is provided in profile data, ALWAYS generate the upload_file command
- DO NOT put file uploads in unmapped_fields if a file path is available

=== SELECTOR RULES ===

Use CSS selectors. Priority:
1. ID: "#elementId"
2. Name: "[name='fieldName']" 
3. Data attrs: "[data-automation-id='value']", "[data-testid='value']"
4. Type+Name: "input[type='file'][name='resume']"
5. Aria: "[aria-label='Upload Resume']"

selector_type is always "css" unless absolutely necessary to use "xpath".

=== OUTPUT JSON FORMAT ===

{
    "platform": "workday",
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
            "action": "upload_file",
            "selector": "input[type='file'][name='resume']",
            "selector_type": "css",
            "file_path": "/path/to/resume.pdf",
            "field_name": "Resume Upload",
            "confidence": 1.0
        },
        {
            "action": "select_option",
            "selector": "#country",
            "selector_type": "css", 
            "value": "United States of America",
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
    
    "apply_button": null,
    
    "next_button": {
        "selector": "button[data-automation-id='bottom-navigation-next-button']",
        "selector_type": "css",
        "text": "Continue"
    },
    
    "submit_button": null,
    
    "navigation_commands": [],
    
    "unmapped_fields": ["How did you hear about us?", "Referral Code"]
}

=== BUTTON DETECTION RULES ===

IMPORTANT: Detect buttons based on their purpose:

1. "apply_button" - ONLY for job listing pages to START the application
   - Text: "Apply", "Apply Now", "Apply for this job", "Start Application", "Begin Application"
   - Usually a prominent CTA button on job description pages
   - Set this ONLY when page_type is "job_listing"

2. "next_button" - For navigating to the NEXT step in a multi-step form
   - Text: "Next", "Continue", "Save and Continue", "Proceed", "Next Step"
   - Found in multi-step application wizards
   
3. "submit_button" - For FINAL submission of the application
   - Text: "Submit", "Submit Application", "Apply", "Finish", "Complete Application"
   - This is the FINAL action button, not for starting or navigating

DO NOT confuse apply_button with submit_button:
- apply_button: Starts the application process (on job listing page)
- submit_button: Completes/submits a filled application (on final form page)

=== CRITICAL RULES ===

1. ALWAYS detect platform from URL FIRST (check URL patterns in JOB PLATFORM DETECTION section)
2. ALWAYS determine page_type before analyzing form fields
3. For job_listing pages: Set is_form_page=false, needs_navigation=true, provide apply_button
4. ONLY fill fields you can CONFIDENTLY match to profile data
5. Use the EXACT selector that will find the element
6. For dropdowns, value is the VISIBLE TEXT of the option
7. For file upload inputs (resume, cover letter): Use upload_file action with the provided file path
8. Return VALID JSON only - no markdown, no comments
9. Set confidence based on how sure you are about the match
10. Only put fields in unmapped_fields if NO matching profile data exists
11. For multi-step forms, provide next_button to navigate to the next step
12. Set platform to "unknown" if you cannot identify the job platform"""


class AIService:
    def __init__(self, api_key: str = None, model: str = None):
        self.api_key = api_key or settings.openai_api_key
        self.model = model or "gpt-4o"
        self.client = None
        
        if self.api_key:
            self.client = openai.OpenAI(api_key=self.api_key)
    
    def _log_openai_request(
        self,
        page_content: Dict[str, Any],
        profile_data: Dict[str, Any],
        prompt: str,
    ) -> None:
        """Log detailed information about the OpenAI request."""
        print("\n" + "="*80)
        print("  [OPENAI REQUEST - DATA BEING SENT]")
        print("="*80)
        
        # Profile data summary
        print("\n  👤 PROFILE DATA:")
        print(f"      Name: {profile_data.get('first_name', '')} {profile_data.get('middle_name', '')} {profile_data.get('last_name', '')}")
        print(f"      Email: {profile_data.get('email', '')}")
        print(f"      Phone: {profile_data.get('phone', '')}")
        print(f"      Address: {profile_data.get('address_1', '')} {profile_data.get('address_2', '')}")
        print(f"      City/State/Zip: {profile_data.get('city', '')}, {profile_data.get('state', '')} {profile_data.get('zip_code', '')}")
        print(f"      Country: {profile_data.get('country', '')}")
        print(f"      LinkedIn: {profile_data.get('linkedin_url', '')}")
        print(f"      GitHub: {profile_data.get('github_url', '')}")
        print(f"      Portfolio: {profile_data.get('portfolio_url', '')}")
        
        # Work experience
        work_exp = profile_data.get('work_experience', [])
        print(f"\n  💼 WORK EXPERIENCE ({len(work_exp)} entries):")
        if work_exp:
            for i, exp in enumerate(work_exp[:3]):
                title = exp.get('job_title', exp.get('title', 'N/A'))
                company = exp.get('company_name', exp.get('company', 'N/A'))
                start = exp.get('start_date', 'N/A')
                end = exp.get('end_date', 'Present')
                print(f"      {i+1}. {title} at {company} ({start} - {end})")
            if len(work_exp) > 3:
                print(f"      ... and {len(work_exp) - 3} more")
        else:
            print("      (No work experience)")
        
        # Education
        education = profile_data.get('education', [])
        print(f"\n  🎓 EDUCATION ({len(education)} entries):")
        if education:
            for i, edu in enumerate(education[:2]):
                degree = edu.get('degree', 'N/A')
                major = edu.get('major', edu.get('field', 'N/A'))
                school = edu.get('university_name', edu.get('school', 'N/A'))
                print(f"      {i+1}. {degree} in {major} from {school}")
            if len(education) > 2:
                print(f"      ... and {len(education) - 2} more")
        else:
            print("      (No education)")
        
        # Skills
        skills = profile_data.get('skills', [])
        print(f"\n  🛠️ SKILLS ({len(skills)} total):")
        if skills:
            skills_preview = ', '.join(skills[:10])
            print(f"      {skills_preview}{'...' if len(skills) > 10 else ''}")
        else:
            print("      (No skills)")
        
        # File paths
        resume_path = profile_data.get('resume_path')
        cover_letter_path = profile_data.get('cover_letter_template_path')
        print(f"\n  📎 FILE PATHS:")
        print(f"      Resume: {resume_path or '(not provided)'}")
        print(f"      Cover Letter: {cover_letter_path or '(not provided)'}")
        
        # Demographics
        gender = profile_data.get('gender')
        nationality = profile_data.get('nationality')
        veteran = profile_data.get('veteran_status')
        disability = profile_data.get('disability_status')
        print(f"\n  👤 DEMOGRAPHICS:")
        print(f"      Gender: {gender or '(not set)'}")
        print(f"      Nationality: {nationality or '(not set)'}")
        print(f"      Veteran: {veteran or '(not set)'}")
        print(f"      Disability: {disability or '(not set)'}")
        
        # Salary
        salary_min = profile_data.get('salary_min')
        salary_max = profile_data.get('salary_max')
        if salary_min or salary_max:
            print(f"\n  💰 SALARY EXPECTATIONS:")
            print(f"      Range: {profile_data.get('salary_currency', 'USD')} {salary_min or 'N/A'} - {salary_max or 'N/A'}")
        
        # Page content summary
        print(f"\n  📄 PAGE CONTENT SUMMARY:")
        print(f"      URL: {page_content.get('url', 'N/A')}")
        print(f"      Title: {page_content.get('title', 'N/A')}")
        print(f"      Inputs: {len(page_content.get('inputs', []))}")
        print(f"      Buttons: {len(page_content.get('buttons', []))}")
        print(f"      Forms: {len(page_content.get('forms', []))}")
        
        # Prompt preview
        print(f"\n  📝 PROMPT LENGTH: {len(prompt):,} characters")
        print(f"\n  📝 FULL PROMPT (for AI):")
        print("-" * 80)
        print(prompt)
        print("-" * 80)
        
        print("\n" + "="*80)
        print("  [END OPENAI REQUEST]")
        print("="*80 + "\n")
    
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
                
                # Mark file inputs clearly for resume/cover letter uploads
                if inp_type == 'file':
                    parts.append("[FILE UPLOAD - use 'upload_file' action]")
                
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
        if profile_data.get('preferred_first_name'):
            lines.append(f"Preferred First Name: {profile_data['preferred_first_name']}")
        lines.append(f"Email: {profile_data.get('email', '')}")
        lines.append(f"Phone: {profile_data.get('phone', '')}")
        if profile_data.get('preferred_password'):
            lines.append(f"Preferred Password (for account creation): {profile_data['preferred_password']}")
        
        if profile_data.get('address_1'):
            lines.append(f"Address Line 1: {profile_data['address_1']}")
        if profile_data.get('address_2'):
            lines.append(f"Address Line 2: {profile_data['address_2']}")
        if profile_data.get('city'):
            lines.append(f"City: {profile_data['city']}")
        if profile_data.get('county'):
            lines.append(f"County: {profile_data['county']}")
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
        
        # Demographics for EEO/voluntary disclosure questions
        if profile_data.get('gender'):
            lines.append(f"Gender: {profile_data['gender']}")
        if profile_data.get('nationality'):
            lines.append(f"Nationality: {profile_data['nationality']}")
        if profile_data.get('veteran_status'):
            lines.append(f"Veteran Status: {profile_data['veteran_status']}")
        if profile_data.get('disability_status'):
            lines.append(f"Disability Status: {profile_data['disability_status']}")
        if profile_data.get('willing_to_travel') is not None:
            lines.append(f"Willing to Travel: {'Yes' if profile_data['willing_to_travel'] else 'No'}")
        if profile_data.get('willing_to_relocate') is not None:
            lines.append(f"Willing to Relocate: {'Yes' if profile_data['willing_to_relocate'] else 'No'}")
        if profile_data.get('primary_language'):
            lines.append(f"Primary Language: {profile_data['primary_language']}")
        
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
        
        # Salary expectations
        salary_min = profile_data.get('salary_min')
        salary_max = profile_data.get('salary_max')
        salary_currency = profile_data.get('salary_currency', 'USD')
        if salary_min or salary_max:
            lines.append("\nSalary Expectations:")
            if salary_min and salary_max:
                lines.append(f"  Range: {salary_currency} {salary_min:,} - {salary_max:,}")
            elif salary_min:
                lines.append(f"  Minimum: {salary_currency} {salary_min:,}")
            elif salary_max:
                lines.append(f"  Maximum: {salary_currency} {salary_max:,}")
        
        # Custom question answers (pre-defined answers for common questions)
        custom_answers = profile_data.get('custom_question_answers', {})
        if custom_answers:
            lines.append("\nPre-defined Answers for Common Questions:")
            for question, answer in list(custom_answers.items())[:10]:
                lines.append(f"  Q: {question}")
                lines.append(f"  A: {answer}")
        
        # File paths for uploads - CRITICAL for resume/cover letter fields
        lines.append("\n=== FILE PATHS FOR UPLOAD ===")
        resume_path = profile_data.get('resume_path')
        cover_letter_path = profile_data.get('cover_letter_template_path')
        
        if resume_path:
            lines.append(f"Resume File Path: {resume_path}")
            lines.append("  -> Use this path for any resume/CV file upload field with action 'upload_file'")
        else:
            lines.append("Resume File Path: (not provided)")
        
        if cover_letter_path:
            lines.append(f"Cover Letter File Path: {cover_letter_path}")
            lines.append("  -> Use this path for any cover letter file upload field with action 'upload_file'")
        else:
            lines.append("Cover Letter File Path: (not provided)")
        
        lines.append("\n=== TASK ===")
        lines.append("Generate autofill commands to fill this form with the profile data.")
        lines.append("For input[type='file'] fields: Use 'upload_file' action with the provided file paths.")
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
            platform=data.get("platform", "unknown"),
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
        
        if data.get("apply_button"):
            ab = data["apply_button"]
            result.apply_button = NavigationButton(
                selector=ab.get("selector", ""),
                selector_type=ab.get("selector_type", "css"),
                text=ab.get("text", ""),
                button_type="apply",
            )
        
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
        
        # Log the prompt being sent to OpenAI
        self._log_openai_request(page_content, profile_data, prompt)
        
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
            print(f"       - platform: {result.platform}")
            print(f"       - is_form_page: {result.is_form_page}")
            print(f"       - page_type: {result.page_type}")
            print(f"       - needs_navigation: {result.needs_navigation}")
            print(f"       - autofill_commands: {len(result.autofill_commands)}")
            print(f"       - apply_button: {result.apply_button.selector if result.apply_button else 'None'}")
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
    ) -> Any:
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
            file_path: Optional[str] = None  # For upload_file action
            
            def to_autofill_command(self) -> Dict[str, Any]:
                cmd = {
                    "action": self.action,
                    "selector": self.selector,
                    "selector_type": self.selector_type,
                }
                if self.action == "upload_file":
                    cmd["file_path"] = self.file_path
                elif self.action in ["type_text", "type_number", "enter_date"]:
                    cmd["value"] = self.value
                elif self.action == "select_option":
                    cmd["value"] = self.value
                    cmd["select_by"] = self.select_by
                elif self.action == "check":
                    cmd["checked"] = self.checked
                elif self.action == "select_radio":
                    cmd["value"] = self.value
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
            platform: str = "unknown"
            is_form_page: bool = True
            needs_navigation: bool = False
            navigation_actions: List = None
            field_mappings: List = None
            unmapped_fields: List[str] = None
            page_type: str = "unknown"
            confidence: float = 0.0
            apply_button: Optional[Dict] = None
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
                file_path=cmd.file_path,  # Include file_path for upload_file action
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
            platform=result.platform,
            is_form_page=result.is_form_page,
            needs_navigation=result.needs_navigation,
            navigation_actions=nav_actions,
            field_mappings=field_mappings,
            unmapped_fields=result.unmapped_fields,
            page_type=result.page_type,
            confidence=result.confidence,
        )
        
        if result.apply_button:
            response.apply_button = {
                "selector": result.apply_button.selector,
                "selector_type": result.apply_button.selector_type,
                "text": result.apply_button.text,
            }
        
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
