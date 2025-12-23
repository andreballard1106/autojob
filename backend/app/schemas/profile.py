"""
Profile Schemas for API Validation
"""

import json
from datetime import datetime
from typing import Any, Optional

from pydantic import BaseModel, EmailStr, Field, field_validator


class DocumentContent(BaseModel):
    """Parsed document content for AI/resume generation."""
    
    filename: str  # Original filename
    path: str  # File path
    content: str  # Parsed text content
    format_type: str = "text"  # pdf, docx, markdown, text


class WorkExperience(BaseModel):
    """Work experience entry with full address and document support."""

    # Basic Info
    company_name: str
    job_title: str
    work_style: str = "onsite"  # remote, hybrid, onsite
    start_date: str
    end_date: Optional[str] = None  # None means current position
    
    # Address
    address_1: Optional[str] = None
    address_2: Optional[str] = None
    city: Optional[str] = None
    state: Optional[str] = None
    country: Optional[str] = None
    zip_code: Optional[str] = None
    
    # Document paths for tailored resume generation
    document_paths: list[str] = Field(default_factory=list)
    
    # Parsed document contents (stored for AI/resume generation)
    document_contents: list[DocumentContent] = Field(default_factory=list)


class Education(BaseModel):
    """Education entry."""

    university_name: str
    degree: str
    major: Optional[str] = None
    location: Optional[str] = None
    start_date: Optional[str] = None
    end_date: Optional[str] = None


class ProfileBase(BaseModel):
    """Base profile schema with common fields."""

    # Name fields
    first_name: str = Field(..., min_length=1, max_length=100)
    middle_name: Optional[str] = Field(None, max_length=100)
    last_name: str = Field(..., min_length=1, max_length=100)
    preferred_first_name: Optional[str] = Field(None, max_length=100)
    
    # Contact
    email: EmailStr
    phone: Optional[str] = Field(None, max_length=50)
    location: Optional[str] = Field(None, max_length=255)  # Simple location for resume
    preferred_password: Optional[str] = Field(None, max_length=255)
    
    # Detailed Address for Job Applications
    address_1: Optional[str] = Field(None, max_length=255)
    address_2: Optional[str] = Field(None, max_length=255)
    county: Optional[str] = Field(None, max_length=100)
    city: Optional[str] = Field(None, max_length=100)
    state: Optional[str] = Field(None, max_length=100)
    country: Optional[str] = Field(None, max_length=100)
    zip_code: Optional[str] = Field(None, max_length=20)
    
    # Online Presence
    linkedin_url: Optional[str] = Field(None, max_length=500)
    github_url: Optional[str] = Field(None, max_length=500)
    portfolio_url: Optional[str] = Field(None, max_length=500)
    
    # Demographics & Work Preferences
    gender: Optional[str] = Field(None, max_length=50)
    nationality: Optional[str] = Field(None, max_length=100)
    veteran_status: Optional[str] = Field(None, max_length=50)
    disability_status: Optional[str] = Field(None, max_length=50)
    willing_to_travel: bool = False
    willing_to_relocate: bool = False
    primary_language: Optional[str] = Field(None, max_length=100)


class ProfileCreate(ProfileBase):
    """Schema for creating a new profile."""

    cover_letter_template: Optional[str] = None
    work_experience: list[WorkExperience] = Field(default_factory=list)
    education: list[Education] = Field(default_factory=list)
    skills: list[str] = Field(default_factory=list)
    custom_fields: dict = Field(default_factory=dict)


class ProfileUpdate(BaseModel):
    """Schema for updating a profile. All fields optional."""

    # Name fields
    first_name: Optional[str] = Field(None, min_length=1, max_length=100)
    middle_name: Optional[str] = Field(None, max_length=100)
    last_name: Optional[str] = Field(None, min_length=1, max_length=100)
    preferred_first_name: Optional[str] = Field(None, max_length=100)
    
    # Contact
    email: Optional[EmailStr] = None
    phone: Optional[str] = Field(None, max_length=50)
    location: Optional[str] = Field(None, max_length=255)
    preferred_password: Optional[str] = Field(None, max_length=255)
    
    # Detailed Address for Job Applications
    address_1: Optional[str] = Field(None, max_length=255)
    address_2: Optional[str] = Field(None, max_length=255)
    county: Optional[str] = Field(None, max_length=100)
    city: Optional[str] = Field(None, max_length=100)
    state: Optional[str] = Field(None, max_length=100)
    country: Optional[str] = Field(None, max_length=100)
    zip_code: Optional[str] = Field(None, max_length=20)
    
    # Online Presence
    linkedin_url: Optional[str] = Field(None, max_length=500)
    github_url: Optional[str] = Field(None, max_length=500)
    portfolio_url: Optional[str] = Field(None, max_length=500)
    
    # Demographics & Work Preferences
    gender: Optional[str] = Field(None, max_length=50)
    nationality: Optional[str] = Field(None, max_length=100)
    veteran_status: Optional[str] = Field(None, max_length=50)
    disability_status: Optional[str] = Field(None, max_length=50)
    willing_to_travel: Optional[bool] = None
    willing_to_relocate: Optional[bool] = None
    primary_language: Optional[str] = Field(None, max_length=100)
    
    # Other fields
    cover_letter_template: Optional[str] = None
    work_experience: Optional[list[WorkExperience]] = None
    education: Optional[list[Education]] = None
    skills: Optional[list[str]] = None
    custom_fields: Optional[dict] = None
    is_active: Optional[bool] = None
    
    # AI Customization (per-profile overrides)
    personal_brand: Optional[str] = None
    key_achievements: Optional[list[str]] = None
    priority_skills: Optional[list[str]] = None
    target_industries: Optional[list[str]] = None
    target_roles: Optional[list[str]] = None
    resume_tone_override: Optional[str] = None
    custom_question_answers: Optional[dict] = None
    salary_min: Optional[int] = None
    salary_max: Optional[int] = None
    salary_currency: Optional[str] = None


def _parse_json_or_list(value: Any) -> list:
    """Parse a value that could be a list, a JSON string, or None."""
    if value is None:
        return []
    if isinstance(value, list):
        return value
    if isinstance(value, str):
        try:
            parsed = json.loads(value)
            return parsed if isinstance(parsed, list) else []
        except (json.JSONDecodeError, TypeError):
            return []
    return []


def _parse_json_or_dict(value: Any) -> dict:
    """Parse a value that could be a dict, a JSON string, or None."""
    if value is None:
        return {}
    if isinstance(value, dict):
        return value
    if isinstance(value, str):
        try:
            parsed = json.loads(value)
            return parsed if isinstance(parsed, dict) else {}
        except (json.JSONDecodeError, TypeError):
            return {}
    return {}


class ProfileResponse(BaseModel):
    """Schema for profile response."""

    id: str
    
    # Name fields
    first_name: str
    middle_name: Optional[str] = None
    last_name: str
    preferred_first_name: Optional[str] = None
    name: str  # Legacy computed field
    
    # Contact
    email: str
    phone: Optional[str] = None
    location: Optional[str] = None
    preferred_password: Optional[str] = None
    
    # Detailed Address for Job Applications
    address_1: Optional[str] = None
    address_2: Optional[str] = None
    county: Optional[str] = None
    city: Optional[str] = None
    state: Optional[str] = None
    country: Optional[str] = None
    zip_code: Optional[str] = None
    
    # Online Presence
    linkedin_url: Optional[str] = None
    github_url: Optional[str] = None
    portfolio_url: Optional[str] = None
    
    # Demographics & Work Preferences
    gender: Optional[str] = None
    nationality: Optional[str] = None
    veteran_status: Optional[str] = None
    disability_status: Optional[str] = None
    willing_to_travel: bool = False
    willing_to_relocate: bool = False
    primary_language: Optional[str] = None
    
    # Documents & Experience
    resume_path: Optional[str] = None
    cover_letter_template: Optional[str] = None
    cover_letter_template_path: Optional[str] = None
    work_experience: list = Field(default_factory=list)
    education: list = Field(default_factory=list)
    skills: list = Field(default_factory=list)
    custom_fields: dict = Field(default_factory=dict)
    
    # AI Customization (per-profile overrides)
    personal_brand: Optional[str] = None
    key_achievements: list = Field(default_factory=list)
    priority_skills: list = Field(default_factory=list)
    target_industries: list = Field(default_factory=list)
    target_roles: list = Field(default_factory=list)
    resume_tone_override: Optional[str] = None
    custom_question_answers: dict = Field(default_factory=dict)
    salary_min: Optional[int] = None
    salary_max: Optional[int] = None
    salary_currency: Optional[str] = None
    
    is_active: bool
    created_at: datetime
    updated_at: datetime

    # Validators to handle string-encoded JSON from database
    @field_validator('work_experience', 'education', 'skills', 'key_achievements', 
                     'priority_skills', 'target_industries', 'target_roles', mode='before')
    @classmethod
    def parse_list_fields(cls, v: Any) -> list:
        return _parse_json_or_list(v)
    
    @field_validator('custom_fields', 'custom_question_answers', mode='before')
    @classmethod
    def parse_dict_fields(cls, v: Any) -> dict:
        return _parse_json_or_dict(v)

    class Config:
        from_attributes = True


class ProfileInternalResponse(BaseModel):
    id: str
    first_name: Optional[str] = None
    middle_name: Optional[str] = None
    last_name: Optional[str] = None
    preferred_first_name: Optional[str] = None
    name: str
    email: str
    phone: Optional[str] = None
    location: Optional[str] = None
    preferred_password: Optional[str] = None
    address_1: Optional[str] = None
    address_2: Optional[str] = None
    county: Optional[str] = None
    city: Optional[str] = None
    state: Optional[str] = None
    country: Optional[str] = None
    zip_code: Optional[str] = None
    linkedin_url: Optional[str] = None
    github_url: Optional[str] = None
    portfolio_url: Optional[str] = None
    gender: Optional[str] = None
    nationality: Optional[str] = None
    veteran_status: Optional[str] = None
    disability_status: Optional[str] = None
    willing_to_travel: bool = False
    willing_to_relocate: bool = False
    primary_language: Optional[str] = None
    work_experience: list = Field(default_factory=list)
    education: list = Field(default_factory=list)
    skills: list = Field(default_factory=list)
    custom_fields: dict = Field(default_factory=dict)
    personal_brand: Optional[str] = None
    key_achievements: list = Field(default_factory=list)
    priority_skills: list = Field(default_factory=list)
    target_industries: list = Field(default_factory=list)
    target_roles: list = Field(default_factory=list)
    resume_tone_override: Optional[str] = None
    custom_question_answers: dict = Field(default_factory=dict)
    salary_min: Optional[int] = None
    salary_max: Optional[int] = None
    salary_currency: Optional[str] = None
    is_active: bool
    created_at: datetime
    updated_at: datetime

    # Validators to handle string-encoded JSON from database
    @field_validator('work_experience', 'education', 'skills', 'key_achievements', 
                     'priority_skills', 'target_industries', 'target_roles', mode='before')
    @classmethod
    def parse_list_fields(cls, v: Any) -> list:
        return _parse_json_or_list(v)
    
    @field_validator('custom_fields', 'custom_question_answers', mode='before')
    @classmethod
    def parse_dict_fields(cls, v: Any) -> dict:
        return _parse_json_or_dict(v)

    class Config:
        from_attributes = True


class ProfileStats(BaseModel):
    """Statistics for a profile."""

    total_applications: int = 0
    pending: int = 0
    in_progress: int = 0
    applied: int = 0
    failed: int = 0
    awaiting_action: int = 0


class ProfileWithStats(ProfileResponse):
    """Profile with application statistics."""

    stats: ProfileStats = Field(default_factory=ProfileStats)


class ProfileListResponse(BaseModel):
    """Response for listing profiles."""

    profiles: list[ProfileResponse]
    total: int
