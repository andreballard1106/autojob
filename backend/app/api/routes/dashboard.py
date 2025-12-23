"""
Dashboard API Routes - Statistics and Overview
"""

from datetime import datetime, timedelta
from typing import Optional

from fastapi import APIRouter, Depends, Query
from sqlalchemy import select, func, case
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models.profile import Profile
from app.models.job import JobApplication, JobStatus
from app.models.application_log import ApplicationLog

router = APIRouter()


@router.get("/stats")
async def get_dashboard_stats(
    profile_id: Optional[str] = None,
    days: int = Query(7, ge=1, le=90),
    db: AsyncSession = Depends(get_db),
):
    """Get overall dashboard statistics."""
    since = datetime.utcnow() - timedelta(days=days)

    # Base query
    base_query = select(JobApplication)
    if profile_id:
        base_query = base_query.where(JobApplication.profile_id == profile_id)

    # Total applications
    total_query = select(func.count(JobApplication.id))
    if profile_id:
        total_query = total_query.where(JobApplication.profile_id == profile_id)
    total = await db.scalar(total_query) or 0

    # Count by status
    status_query = (
        select(JobApplication.status, func.count(JobApplication.id))
        .group_by(JobApplication.status)
    )
    if profile_id:
        status_query = status_query.where(JobApplication.profile_id == profile_id)

    result = await db.execute(status_query)
    status_counts = {row[0]: row[1] for row in result.all()}

    # Recent applications (in date range)
    recent_query = select(func.count(JobApplication.id)).where(
        JobApplication.created_at >= since
    )
    if profile_id:
        recent_query = recent_query.where(JobApplication.profile_id == profile_id)
    recent = await db.scalar(recent_query) or 0

    # Success rate
    applied = status_counts.get(JobStatus.APPLIED.value, 0)
    failed = status_counts.get(JobStatus.FAILED.value, 0)
    completed = applied + failed
    success_rate = (applied / completed * 100) if completed > 0 else 0

    # Awaiting action
    awaiting_action = sum(status_counts.get(s, 0) for s in JobStatus.awaiting_statuses())

    return {
        "total_applications": total,
        "recent_applications": recent,
        "by_status": {
            "pending": status_counts.get(JobStatus.PENDING.value, 0) +
                      status_counts.get(JobStatus.QUEUED.value, 0),
            "in_progress": status_counts.get(JobStatus.IN_PROGRESS.value, 0),
            "applied": applied,
            "failed": failed,
            "awaiting_action": awaiting_action,
            "cancelled": status_counts.get(JobStatus.CANCELLED.value, 0),
        },
        "success_rate": round(success_rate, 1),
        "period_days": days,
    }


@router.get("/team")
async def get_team_overview(
    db: AsyncSession = Depends(get_db),
):
    """Get overview of all team members with their stats."""
    # Get all active profiles with their application counts
    query = (
        select(
            Profile.id,
            Profile.name,
            Profile.email,
            func.count(JobApplication.id).label("total_apps"),
            func.sum(
                case(
                    (JobApplication.status == JobStatus.APPLIED.value, 1),
                    else_=0
                )
            ).label("applied"),
            func.sum(
                case(
                    (JobApplication.status == JobStatus.PENDING.value, 1),
                    (JobApplication.status == JobStatus.QUEUED.value, 1),
                    else_=0
                )
            ).label("pending"),
            func.sum(
                case(
                    (JobApplication.status == JobStatus.IN_PROGRESS.value, 1),
                    else_=0
                )
            ).label("in_progress"),
            func.sum(
                case(
                    (JobApplication.status.in_(JobStatus.awaiting_statuses()), 1),
                    else_=0
                )
            ).label("awaiting_action"),
        )
        .outerjoin(JobApplication, Profile.id == JobApplication.profile_id)
        .where(Profile.is_active == True)
        .group_by(Profile.id, Profile.name, Profile.email)
        .order_by(Profile.name)
    )

    result = await db.execute(query)
    rows = result.all()

    team = []
    for row in rows:
        team.append({
            "id": str(row.id),
            "name": row.name,
            "email": row.email,
            "stats": {
                "total": row.total_apps or 0,
                "applied": row.applied or 0,
                "pending": row.pending or 0,
                "in_progress": row.in_progress or 0,
                "awaiting_action": row.awaiting_action or 0,
            }
        })

    return {"team": team, "total_members": len(team)}


@router.get("/activity")
async def get_activity_feed(
    limit: int = Query(50, ge=1, le=200),
    profile_id: Optional[str] = None,
    db: AsyncSession = Depends(get_db),
):
    """Get recent activity across all applications."""
    query = (
        select(
            ApplicationLog.id,
            ApplicationLog.action,
            ApplicationLog.details,
            ApplicationLog.created_at,
            JobApplication.job_title,
            JobApplication.company_name,
            JobApplication.url,
            Profile.name.label("profile_name"),
        )
        .join(JobApplication, ApplicationLog.application_id == JobApplication.id)
        .join(Profile, JobApplication.profile_id == Profile.id)
        .order_by(ApplicationLog.created_at.desc())
        .limit(limit)
    )

    if profile_id:
        query = query.where(JobApplication.profile_id == profile_id)

    result = await db.execute(query)
    rows = result.all()

    activities = []
    for row in rows:
        activities.append({
            "id": str(row.id),
            "action": row.action,
            "details": row.details,
            "created_at": row.created_at.isoformat(),
            "job": {
                "title": row.job_title,
                "company": row.company_name,
                "url": row.url,
            },
            "profile": row.profile_name,
        })

    return {"activities": activities}


@router.get("/charts/applications-over-time")
async def get_applications_chart(
    days: int = Query(30, ge=7, le=90),
    profile_id: Optional[str] = None,
    db: AsyncSession = Depends(get_db),
):
    """Get application counts by day for charting."""
    since = datetime.utcnow() - timedelta(days=days)

    query = (
        select(
            func.date(JobApplication.created_at).label("date"),
            func.count(JobApplication.id).label("count"),
        )
        .where(JobApplication.created_at >= since)
        .group_by(func.date(JobApplication.created_at))
        .order_by(func.date(JobApplication.created_at))
    )

    if profile_id:
        query = query.where(JobApplication.profile_id == profile_id)

    result = await db.execute(query)
    rows = result.all()

    data = [
        {"date": str(row.date), "count": row.count}
        for row in rows
    ]

    return {"data": data, "period_days": days}
