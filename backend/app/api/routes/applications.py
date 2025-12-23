"""
Applications API Routes - Status updates and logs
"""

from fastapi import APIRouter, Depends, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models.application_log import ApplicationLog
from app.api.helpers import get_application_or_404

router = APIRouter()


@router.get("/{application_id}/logs")
async def get_application_logs(
    application_id: str,
    limit: int = Query(100, ge=1, le=500),
    db: AsyncSession = Depends(get_db),
):
    """Get logs for a specific application."""
    await get_application_or_404(db, application_id)

    query = (
        select(ApplicationLog)
        .where(ApplicationLog.application_id == application_id)
        .order_by(ApplicationLog.created_at.desc())
        .limit(limit)
    )

    result = await db.execute(query)
    logs = result.scalars().all()

    return {
        "application_id": application_id,
        "logs": [
            {
                "id": str(log.id),
                "action": log.action,
                "details": log.details,
                "screenshot_path": log.screenshot_path,
                "created_at": log.created_at.isoformat(),
            }
            for log in logs
        ],
    }


@router.get("/{application_id}/screenshots")
async def get_application_screenshots(
    application_id: str,
    db: AsyncSession = Depends(get_db),
):
    """Get all screenshots for an application."""
    await get_application_or_404(db, application_id)

    query = (
        select(ApplicationLog)
        .where(
            ApplicationLog.application_id == application_id,
            ApplicationLog.screenshot_path.isnot(None),
        )
        .order_by(ApplicationLog.created_at.asc())
    )

    result = await db.execute(query)
    logs = result.scalars().all()

    return {
        "application_id": application_id,
        "screenshots": [
            {
                "path": log.screenshot_path,
                "action": log.action,
                "created_at": log.created_at.isoformat(),
            }
            for log in logs
        ],
    }
