"""
Profile Model - Represents a team member/applicant
"""

from datetime import datetime
from typing import Optional, TYPE_CHECKING

from sqlalchemy import Boolean, DateTime, String, Text, JSON, Integer
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.config import settings
from app.database import Base
from app.utils import generate_uuid

if TYPE_CHECKING:
    from app.models.job import JobApplication


class Profile(Base):
    """
    User profile containing personal information, resume, and application data.
    Each profile represents a team member who can apply to jobs.
    """

    __tablename__ = "profiles"

    # Primary key
    id: Mapped[str] = mapped_column(
        String(36),
        primary_key=True,
        default=generate_uuid,
    )

    # ============================================
    # 1. USER INFO SECTION
    # ============================================
    
    # Basic Name Information
    first_name: Mapped[str] = mapped_column(String(100), nullable=False)
    middle_name: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    last_name: Mapped[str] = mapped_column(String(100), nullable=False)
    preferred_first_name: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    
    # Legacy field for display name (computed from first + last)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    
    # Contact Information
    email: Mapped[str] = mapped_column(String(255), nullable=False, unique=True)
    phone: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    location: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)  # Simple location for resume display
    preferred_password: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)  # For auto-filling account creation forms
    
    # Detailed Address for Job Application Forms
    address_1: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    address_2: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    county: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    city: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    state: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    country: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    zip_code: Mapped[Optional[str]] = mapped_column(String(20), nullable=True)
    
    # Online Presence
    linkedin_url: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    github_url: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    portfolio_url: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    
    # Demographics & Work Preferences
    gender: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)  # male, female, non-binary, prefer_not_to_say
    nationality: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    veteran_status: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)  # yes, no, prefer_not_to_say
    disability_status: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)  # yes, no, prefer_not_to_say
    willing_to_travel: Mapped[bool] = mapped_column(Boolean, default=False)
    willing_to_relocate: Mapped[bool] = mapped_column(Boolean, default=False)
    primary_language: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    
    # ============================================
    # 2. WORK HISTORY SECTION (JSON array)
    # ============================================
    # Each work history entry contains:
    # - company_name, job_title, work_style (remote/hybrid/onsite)
    # - start_date, end_date
    # - address_1, address_2, city, state, country, zip_code
    # - document_paths (array of uploaded file paths for tailored resume generation)
    work_experience: Mapped[Optional[dict]] = mapped_column(
        JSON,
        default=list,
        nullable=True,
    )
    
    # ============================================
    # 3. EDUCATION SECTION (JSON array)
    # ============================================
    # Each education entry contains:
    # - university_name, degree, major, location
    # - start_date, end_date
    education: Mapped[Optional[dict]] = mapped_column(
        JSON,
        default=list,
        nullable=True,
    )
    
    # ============================================
    # ADDITIONAL FIELDS
    # ============================================
    
    # Skills
    skills: Mapped[Optional[dict]] = mapped_column(
        JSON,
        default=list,
        nullable=True,
    )

    # Documents
    resume_path: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    cover_letter_template: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    cover_letter_template_path: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)

    # Additional custom fields for form filling
    custom_fields: Mapped[Optional[dict]] = mapped_column(
        JSON,
        default=dict,
        nullable=True,
    )

    # ============================================
    # AI CUSTOMIZATION (Per-Profile Overrides)
    # ============================================
    
    # Personal Brand Statement (used for AI context)
    personal_brand: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    
    # Key achievements to always highlight
    key_achievements: Mapped[Optional[dict]] = mapped_column(
        JSON,
        default=list,
        nullable=True,
    )
    
    # Skills to emphasize in applications
    priority_skills: Mapped[Optional[dict]] = mapped_column(
        JSON,
        default=list,
        nullable=True,
    )
    
    # Target industries/roles (helps AI tailor responses)
    target_industries: Mapped[Optional[dict]] = mapped_column(
        JSON,
        default=list,
        nullable=True,
    )
    
    target_roles: Mapped[Optional[dict]] = mapped_column(
        JSON,
        default=list,
        nullable=True,
    )
    
    # Preferred resume tone override
    resume_tone_override: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    
    # Custom question answers (profile-specific overrides)
    # Stored as JSON: { "question_key": "custom_answer" }
    custom_question_answers: Mapped[Optional[dict]] = mapped_column(
        JSON,
        default=dict,
        nullable=True,
    )
    
    # Salary expectations
    salary_min: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    salary_max: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    salary_currency: Mapped[Optional[str]] = mapped_column(String(10), default="USD", nullable=True)

    # Status
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)

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

    # Relationships
    job_applications: Mapped[list["JobApplication"]] = relationship(
        "JobApplication",
        back_populates="profile",
        cascade="all, delete-orphan",
    )

    def __repr__(self) -> str:
        return f"<Profile {self.name} ({self.email})>"
    
    @property
    def display_name(self) -> str:
        """Get the display name (preferred or first + last)."""
        if self.preferred_first_name:
            return f"{self.preferred_first_name} {self.last_name}"
        return f"{self.first_name} {self.last_name}"
