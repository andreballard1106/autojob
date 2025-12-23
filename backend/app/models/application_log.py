"""
ApplicationLog Model - Activity logs for job applications
"""

from datetime import datetime
from typing import TYPE_CHECKING, Optional

from sqlalchemy import DateTime, ForeignKey, String, JSON
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base
from app.utils import generate_uuid

if TYPE_CHECKING:
    from app.models.job import JobApplication


class ApplicationLog(Base):
    """
    Detailed activity log for each job application.
    Used for debugging, auditing, and progress tracking.
    """

    __tablename__ = "application_logs"

    # Primary key
    id: Mapped[str] = mapped_column(
        String(36),
        primary_key=True,
        default=generate_uuid,
    )

    # Foreign key to job application
    application_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("job_applications.id", ondelete="CASCADE"),
        nullable=False,
    )

    # Log details
    action: Mapped[str] = mapped_column(String(100), nullable=False)
    details: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)
    screenshot_path: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)

    # Timestamp
    created_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=datetime.utcnow,
    )

    # Relationships
    application: Mapped["JobApplication"] = relationship(
        "JobApplication", back_populates="logs"
    )

    def __repr__(self) -> str:
        return f"<ApplicationLog {self.action} at {self.created_at}>"
