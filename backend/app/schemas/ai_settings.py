"""
AI Settings Schemas for API Validation
"""

from datetime import datetime
from typing import Optional

from pydantic import BaseModel


class AISettingsUpdate(BaseModel):
    """Schema for updating AI settings. All fields optional."""
    
    # AI Provider Configuration
    openai_api_key: Optional[str] = None
    openai_model: Optional[str] = None
    temperature: Optional[float] = None
    max_tokens: Optional[int] = None
    
    # Feature Toggles
    enable_resume_generation: Optional[bool] = None
    enable_cover_letter_generation: Optional[bool] = None
    enable_answer_generation: Optional[bool] = None
    
    # Resume Settings
    resume_system_prompt: Optional[str] = None
    resume_tone: Optional[str] = None
    resume_format: Optional[str] = None
    resume_max_pages: Optional[int] = None
    
    # Cover Letter Settings
    cover_letter_system_prompt: Optional[str] = None
    cover_letter_tone: Optional[str] = None
    cover_letter_length: Optional[str] = None
    
    # Question Prompts
    question_prompts: Optional[dict] = None
    
    # Default Answers
    default_answers: Optional[dict] = None
    
    # Browser Automation Settings
    max_concurrent_jobs: Optional[int] = None
    browser_timeout: Optional[int] = None
    browser_headless: Optional[bool] = None
    screenshot_on_error: Optional[bool] = None
    auto_retry_failed: Optional[bool] = None
    max_retries: Optional[int] = None
    
    # Fallback Settings
    ai_timeout_seconds: Optional[int] = None
    use_fallback_on_error: Optional[bool] = None


class AISettingsPublicResponse(BaseModel):
    """Public response with masked API key."""
    
    id: str
    
    # Show masked API key
    openai_api_key_masked: Optional[str] = None
    openai_model: str
    temperature: float
    max_tokens: int
    
    # Feature Toggles
    enable_resume_generation: bool
    enable_cover_letter_generation: bool
    enable_answer_generation: bool
    
    # Resume Settings
    resume_system_prompt: Optional[str] = None
    resume_tone: str
    resume_format: str
    resume_max_pages: int
    
    # Cover Letter Settings
    cover_letter_system_prompt: Optional[str] = None
    cover_letter_tone: str
    cover_letter_length: str
    
    # Question Prompts
    question_prompts: dict
    
    # Default Answers
    default_answers: dict
    
    # Browser Automation Settings
    max_concurrent_jobs: int
    browser_timeout: int
    browser_headless: bool
    screenshot_on_error: bool
    auto_retry_failed: bool
    max_retries: int
    
    # Fallback Settings
    ai_timeout_seconds: int
    use_fallback_on_error: bool
    
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


# Default prompts for the frontend
DEFAULT_QUESTION_PROMPTS_LIST = [
    {
        "key": "why_work_here",
        "name": "Why do you want to work here?",
        "description": "Generate response about interest in the company",
    },
    {
        "key": "tell_about_yourself",
        "name": "Tell me about yourself",
        "description": "Professional summary and background",
    },
    {
        "key": "greatest_strengths",
        "name": "What are your greatest strengths?",
        "description": "Highlight top skills and qualities",
    },
    {
        "key": "greatest_weakness",
        "name": "What is your greatest weakness?",
        "description": "Show self-awareness and growth mindset",
    },
    {
        "key": "why_leaving",
        "name": "Why are you leaving your current job?",
        "description": "Positive response about seeking new opportunities",
    },
    {
        "key": "five_year_plan",
        "name": "Where do you see yourself in 5 years?",
        "description": "Career goals and ambitions",
    },
    {
        "key": "challenge_overcome",
        "name": "Describe a challenge you overcame",
        "description": "STAR-format response about problem solving",
    },
    {
        "key": "salary_expectations",
        "name": "What are your salary expectations?",
        "description": "Diplomatic response about compensation",
    },
    {
        "key": "why_hire_you",
        "name": "Why should we hire you?",
        "description": "Compelling pitch for candidacy",
    },
    {
        "key": "questions_for_us",
        "name": "Do you have any questions for us?",
        "description": "Thoughtful questions to ask interviewer",
    },
]

DEFAULT_FORM_FIELDS_LIST = [
    {"key": "work_authorization", "name": "Work Authorization", "type": "text"},
    {"key": "sponsorship_required", "name": "Sponsorship Required", "type": "select"},
    {"key": "willing_to_relocate", "name": "Willing to Relocate", "type": "select"},
    {"key": "willing_to_travel", "name": "Willing to Travel", "type": "select"},
    {"key": "can_start_immediately", "name": "Start Date", "type": "text"},
    {"key": "criminal_background", "name": "Criminal Background", "type": "select"},
    {"key": "drug_test", "name": "Drug Test Consent", "type": "select"},
    {"key": "background_check", "name": "Background Check Consent", "type": "select"},
    {"key": "non_compete", "name": "Non-Compete Agreement", "type": "select"},
    {"key": "how_did_you_hear", "name": "How Did You Hear About Us", "type": "text"},
]

