"""
Job Application Schemas for API Validation
"""

import json
from datetime import datetime
from typing import Any, Optional
from uuid import UUID

from pydantic import BaseModel, Field, field_validator

from app.models.job import JobStatus


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


class JobBase(BaseModel):
    """Base job schema with common fields."""

    url: str = Field(..., min_length=1, max_length=2000)
    priority: int = Field(default=0, ge=0, le=100)


class JobCreate(JobBase):
    """Schema for creating a single job application."""

    profile_id: UUID

    @field_validator("url")
    @classmethod
    def validate_url(cls, v: str) -> str:
        """Basic URL validation."""
        v = v.strip()
        if not v.startswith(("http://", "https://")):
            raise ValueError("URL must start with http:// or https://")
        return v


class JobBulkCreate(BaseModel):
    """Schema for bulk creating job applications."""

    profile_id: UUID
    urls: list[str] = Field(..., min_length=1)
    priority: int = Field(default=0, ge=0, le=100)

    @field_validator("urls")
    @classmethod
    def validate_urls(cls, v: list[str]) -> list[str]:
        """Validate and clean URLs."""
        cleaned = []
        for url in v:
            url = url.strip()
            if url and url.startswith(("http://", "https://")):
                cleaned.append(url)
        if not cleaned:
            raise ValueError("At least one valid URL is required")
        return cleaned


class JobUpdate(BaseModel):
    """Schema for updating a job application."""

    priority: Optional[int] = Field(None, ge=0, le=100)
    status: Optional[JobStatus] = None
    error_message: Optional[str] = None


class JobLogResponse(BaseModel):
    """Schema for application log entry."""

    id: str
    action: str
    details: Optional[dict] = None
    screenshot_path: Optional[str] = None
    created_at: datetime

    # Validator to handle string-encoded JSON from database
    @field_validator('details', mode='before')
    @classmethod
    def parse_details(cls, v: Any) -> Optional[dict]:
        if v is None:
            return None
        return _parse_json_or_dict(v)

    class Config:
        from_attributes = True


class JobResponse(BaseModel):
    """Schema for job application response."""

    id: str
    profile_id: str
    url: str
    url_hash: str
    company_name: Optional[str] = None
    job_title: Optional[str] = None
    location: Optional[str] = None
    salary_range: Optional[str] = None
    status: str
    error_message: Optional[str] = None
    confirmation_reference: Optional[str] = None
    retry_count: int
    max_retries: int
    priority: int
    extra_data: Optional[dict] = None
    created_at: datetime
    updated_at: datetime
    started_at: Optional[datetime] = None
    applied_at: Optional[datetime] = None

    # Validator to handle string-encoded JSON from database
    @field_validator('extra_data', mode='before')
    @classmethod
    def parse_extra_data(cls, v: Any) -> Optional[dict]:
        if v is None:
            return None
        return _parse_json_or_dict(v)

    class Config:
        from_attributes = True


class JobDetailResponse(JobResponse):
    """Job response with logs included."""

    logs: list[JobLogResponse] = Field(default_factory=list)


class JobListResponse(BaseModel):
    """Response for listing jobs."""

    jobs: list[JobResponse]
    total: int
    page: int
    page_size: int
    total_pages: int


class BulkCreateResponse(BaseModel):
    """Response for bulk job creation."""

    created: int
    duplicates: int
    errors: int
    job_ids: list[str]
    duplicate_urls: list[str] = Field(default_factory=list)
    error_messages: list[str] = Field(default_factory=list)
