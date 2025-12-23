"""
JobApplication Model - Represents a job application task
"""

import hashlib
from datetime import datetime
from enum import Enum
from typing import TYPE_CHECKING, Optional, List

from sqlalchemy import DateTime, ForeignKey, Integer, String, Text, JSON, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base
from app.utils import generate_uuid

if TYPE_CHECKING:
    from app.models.profile import Profile
    from app.models.application_log import ApplicationLog


class JobStatus(str, Enum):
    PENDING = "pending"
    QUEUED = "queued"
    IN_PROGRESS = "in_progress"
    AWAITING_OTP = "awaiting_otp"
    AWAITING_CAPTCHA = "awaiting_captcha"
    AWAITING_USER = "awaiting_user"
    AWAITING_ACTION = "awaiting_action"
    SUBMITTED = "submitted"
    APPLIED = "applied"
    FAILED = "failed"
    CANCELLED = "cancelled"
    DUPLICATE = "duplicate"

    @classmethod
    def awaiting_statuses(cls) -> List[str]:
        return [
            cls.AWAITING_OTP.value,
            cls.AWAITING_CAPTCHA.value,
            cls.AWAITING_USER.value,
            cls.AWAITING_ACTION.value,
        ]


class JobApplication(Base):
    """
    Represents a single job application task.
    Tracks the URL, status, and metadata for each application.
    """

    __tablename__ = "job_applications"

    # Primary key
    id: Mapped[str] = mapped_column(
        String(36),
        primary_key=True,
        default=generate_uuid,
    )

    # Foreign key to profile
    profile_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("profiles.id", ondelete="CASCADE"),
        nullable=False,
    )

    # Job URL and hash for duplicate detection
    url: Mapped[str] = mapped_column(String(2000), nullable=False)
    url_hash: Mapped[str] = mapped_column(String(64), nullable=False)

    # Job Details (scraped from the page if possible)
    company_name: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    job_title: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    location: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    salary_range: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)

    # Application Status
    status: Mapped[str] = mapped_column(
        String(50),
        default=JobStatus.PENDING.value,
        nullable=False,
    )
    error_message: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    confirmation_reference: Mapped[Optional[str]] = mapped_column(
        String(255), nullable=True
    )

    # Retry handling
    retry_count: Mapped[int] = mapped_column(Integer, default=0)
    max_retries: Mapped[int] = mapped_column(Integer, default=3)

    # Priority (higher = more priority)
    priority: Mapped[int] = mapped_column(Integer, default=0)

    # Browser session tracking
    browser_session_id: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)

    # Additional data
    extra_data: Mapped[Optional[dict]] = mapped_column(JSON, default=dict, nullable=True)

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
    started_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime, nullable=True
    )
    applied_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime, nullable=True
    )

    # Relationships
    profile: Mapped["Profile"] = relationship("Profile", back_populates="job_applications")
    logs: Mapped[list["ApplicationLog"]] = relationship(
        "ApplicationLog",
        back_populates="application",
        cascade="all, delete-orphan",
        order_by="ApplicationLog.created_at",
    )

    # Unique constraint: one application per profile per URL
    __table_args__ = (
        UniqueConstraint("profile_id", "url_hash", name="uq_profile_url"),
    )

    @staticmethod
    def generate_url_hash(url: str) -> str:
        """Generate SHA256 hash of URL for duplicate detection."""
        # Normalize URL (remove trailing slashes, lowercase)
        normalized = url.strip().rstrip("/").lower()
        return hashlib.sha256(normalized.encode()).hexdigest()

    def __repr__(self) -> str:
        return f"<JobApplication {self.job_title or 'Unknown'} at {self.company_name or 'Unknown'} ({self.status})>"
