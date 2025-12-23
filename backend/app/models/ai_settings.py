"""
AI Settings Model - Stores AI configuration and prompt templates

Supports global settings and per-profile customization.
"""

from datetime import datetime
from typing import Optional

from sqlalchemy import Boolean, DateTime, String, Text, Integer, Float, JSON
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base
from app.utils import generate_uuid


class AISettings(Base):
    """
    Global AI settings for the application.
    Only one record should exist (singleton pattern).
    """
    __tablename__ = "ai_settings"

    id: Mapped[str] = mapped_column(
        String(36),
        primary_key=True,
        default=generate_uuid,
    )

    # ============================================
    # AI PROVIDER CONFIGURATION
    # ============================================
    
    # OpenAI Settings
    openai_api_key: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    openai_model: Mapped[str] = mapped_column(String(50), default="gpt-4o")
    temperature: Mapped[float] = mapped_column(Float, default=0.7)
    max_tokens: Mapped[int] = mapped_column(Integer, default=2000)
    
    # AI Feature Toggles
    enable_resume_generation: Mapped[bool] = mapped_column(Boolean, default=True)
    enable_cover_letter_generation: Mapped[bool] = mapped_column(Boolean, default=True)
    enable_answer_generation: Mapped[bool] = mapped_column(Boolean, default=True)
    
    # ============================================
    # RESUME GENERATION PROMPTS
    # ============================================
    
    resume_system_prompt: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    resume_tone: Mapped[str] = mapped_column(String(50), default="professional")  # professional, creative, technical, executive
    resume_format: Mapped[str] = mapped_column(String(50), default="bullet")  # bullet, narrative, hybrid
    resume_max_pages: Mapped[int] = mapped_column(Integer, default=2)
    
    # ============================================
    # COVER LETTER PROMPTS
    # ============================================
    
    cover_letter_system_prompt: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    cover_letter_tone: Mapped[str] = mapped_column(String(50), default="professional")
    cover_letter_length: Mapped[str] = mapped_column(String(50), default="medium")  # short, medium, long
    
    # ============================================
    # COMMON QUESTION PROMPTS (JSON)
    # ============================================
    # Stored as JSON: { "question_key": "prompt_template" }
    
    question_prompts: Mapped[Optional[dict]] = mapped_column(
        JSON,
        default=dict,
        nullable=True,
    )
    
    # ============================================
    # DEFAULT ANSWERS FOR COMMON FIELDS
    # ============================================
    # Stored as JSON: { "field_key": "default_value" }
    
    default_answers: Mapped[Optional[dict]] = mapped_column(
        JSON,
        default=dict,
        nullable=True,
    )
    
    # ============================================
    # BROWSER AUTOMATION SETTINGS
    # ============================================
    
    max_concurrent_jobs: Mapped[int] = mapped_column(Integer, default=5)
    browser_timeout: Mapped[int] = mapped_column(Integer, default=300)
    browser_headless: Mapped[bool] = mapped_column(Boolean, default=False)
    screenshot_on_error: Mapped[bool] = mapped_column(Boolean, default=True)
    auto_retry_failed: Mapped[bool] = mapped_column(Boolean, default=True)
    max_retries: Mapped[int] = mapped_column(Integer, default=3)
    
    # ============================================
    # FALLBACK SETTINGS
    # ============================================
    
    ai_timeout_seconds: Mapped[int] = mapped_column(Integer, default=60)
    use_fallback_on_error: Mapped[bool] = mapped_column(Boolean, default=True)
    
    # Timestamps
    created_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=datetime.utcnow,
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=datetime.utcnow,
        onupdate=datetime.utcnow,
    )

    def __repr__(self) -> str:
        return f"<AISettings model={self.openai_model}>"


# Default question prompts
DEFAULT_QUESTION_PROMPTS = {
    "why_work_here": """Based on the company name "{company_name}" and job title "{job_title}", generate a compelling answer explaining why the candidate wants to work there. Use their background: {profile_summary}. Keep it concise (2-3 sentences).""",
    
    "tell_about_yourself": """Create a professional summary for {name} based on their work experience: {work_experience}. Focus on relevant skills for the {job_title} role. Keep it under 150 words.""",
    
    "greatest_strengths": """Based on {name}'s skills ({skills}) and work experience ({work_experience}), identify and articulate their top 3 strengths relevant to {job_title}. Be specific with examples.""",
    
    "greatest_weakness": """Generate a professional answer about a weakness that shows self-awareness and growth mindset. The weakness should be genuine but not disqualifying for {job_title}. Include how they're working to improve.""",
    
    "why_leaving": """Create a professional, positive response about why {name} is looking for new opportunities. Focus on growth, new challenges, and career advancement. Never speak negatively about previous employers.""",
    
    "five_year_plan": """Generate a response about {name}'s 5-year career goals that aligns with the {job_title} role and shows ambition while being realistic. Connect to the company's growth potential.""",
    
    "challenge_overcome": """Based on {name}'s work experience ({work_experience}), create a STAR-format response about overcoming a professional challenge. Make it specific and results-oriented.""",
    
    "salary_expectations": """Provide a diplomatic response about salary expectations for {job_title}. Use the range {salary_range} if provided, otherwise suggest researching market rates. Be flexible but confident.""",
    
    "why_hire_you": """Create a compelling pitch for why {company_name} should hire {name} for {job_title}. Highlight unique value proposition based on: {skills} and {work_experience}.""",
    
    "questions_for_us": """Generate 2-3 thoughtful questions that {name} could ask about {company_name} and the {job_title} role. Focus on growth, team culture, and success metrics.""",
}

# Default answers for common form fields
DEFAULT_FORM_ANSWERS = {
    "work_authorization": "Yes, I am authorized to work in this country",
    "sponsorship_required": "No",
    "willing_to_relocate": "Yes",
    "willing_to_travel": "Yes",
    "can_start_immediately": "Yes, I can start within 2 weeks",
    "criminal_background": "No",
    "drug_test": "Yes, I am willing to undergo a drug test",
    "background_check": "Yes, I consent to a background check",
    "non_compete": "No, I am not bound by any non-compete agreements",
    "how_did_you_hear": "Job Board",
}

