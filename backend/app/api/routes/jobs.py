"""
Job Application Management API Routes
"""

from typing import Optional

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Query, status
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.database import get_db
from app.models.job import JobApplication, JobStatus
from app.models.profile import Profile
from app.api.helpers import get_profile_or_404, get_job_or_404
from app.schemas.job import (
    JobCreate,
    JobBulkCreate,
    JobUpdate,
    JobResponse,
    JobDetailResponse,
    JobListResponse,
    BulkCreateResponse,
)

router = APIRouter()


@router.get("", response_model=JobListResponse)
async def list_jobs(
    profile_id: Optional[str] = None,
    status_filter: Optional[list[str]] = Query(None, alias="status"),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
):
    """List job applications with filtering and pagination."""
    query = select(JobApplication)

    if profile_id:
        query = query.where(JobApplication.profile_id == profile_id)
    if status_filter:
        query = query.where(JobApplication.status.in_(status_filter))

    # Get total count
    count_query = select(func.count(JobApplication.id))
    if profile_id:
        count_query = count_query.where(JobApplication.profile_id == profile_id)
    if status_filter:
        count_query = count_query.where(JobApplication.status.in_(status_filter))
    total = await db.scalar(count_query) or 0

    # Order and paginate
    query = query.order_by(
        JobApplication.priority.desc(),
        JobApplication.created_at.desc(),
    )
    offset = (page - 1) * page_size
    query = query.offset(offset).limit(page_size)

    result = await db.execute(query)
    jobs = result.scalars().all()

    return JobListResponse(
        jobs=[JobResponse.model_validate(j) for j in jobs],
        total=total,
        page=page,
        page_size=page_size,
        total_pages=(total + page_size - 1) // page_size,
    )


@router.post("", response_model=JobResponse, status_code=status.HTTP_201_CREATED)
async def create_job(
    job_data: JobCreate,
    db: AsyncSession = Depends(get_db),
):
    """Create a single job application."""
    profile_id = str(job_data.profile_id)
    
    await get_profile_or_404(db, profile_id)

    # Check duplicate
    url_hash = JobApplication.generate_url_hash(job_data.url)
    existing = await db.scalar(
        select(JobApplication).where(
            JobApplication.profile_id == profile_id,
            JobApplication.url_hash == url_hash,
        )
    )
    if existing:
        raise HTTPException(status_code=409, detail="Job already added for this profile")

    job = JobApplication(
        profile_id=profile_id,
        url=job_data.url,
        url_hash=url_hash,
        priority=job_data.priority,
        status=JobStatus.PENDING.value,
    )

    db.add(job)
    await db.flush()
    await db.refresh(job)

    return JobResponse.model_validate(job)


@router.post("/bulk", response_model=BulkCreateResponse, status_code=status.HTTP_201_CREATED)
async def create_jobs_bulk(
    data: JobBulkCreate,
    db: AsyncSession = Depends(get_db),
):
    """Bulk create job applications."""
    profile_id = str(data.profile_id)
    
    await get_profile_or_404(db, profile_id)

    created_jobs = []
    duplicate_urls = []
    error_messages = []

    for url in data.urls:
        try:
            url_hash = JobApplication.generate_url_hash(url)
            existing = await db.scalar(
                select(JobApplication).where(
                    JobApplication.profile_id == profile_id,
                    JobApplication.url_hash == url_hash,
                )
            )
            if existing:
                duplicate_urls.append(url)
                continue

            job = JobApplication(
                profile_id=profile_id,
                url=url,
                url_hash=url_hash,
                priority=data.priority,
                status=JobStatus.PENDING.value,
            )
            db.add(job)
            await db.flush()
            created_jobs.append(job)
        except Exception as e:
            error_messages.append(f"{url}: {str(e)}")

    return BulkCreateResponse(
        created=len(created_jobs),
        duplicates=len(duplicate_urls),
        errors=len(error_messages),
        job_ids=[j.id for j in created_jobs],
        duplicate_urls=duplicate_urls,
        error_messages=error_messages,
    )


@router.get("/{job_id}", response_model=JobDetailResponse)
async def get_job(
    job_id: str,
    db: AsyncSession = Depends(get_db),
):
    """Get a job application by ID."""
    await get_job_or_404(db, job_id)
    
    query = (
        select(JobApplication)
        .options(selectinload(JobApplication.logs))
        .where(JobApplication.id == job_id)
    )
    result = await db.execute(query)
    job = result.scalar_one_or_none()

    return JobDetailResponse.model_validate(job)


@router.put("/{job_id}", response_model=JobResponse)
async def update_job(
    job_id: str,
    job_data: JobUpdate,
    db: AsyncSession = Depends(get_db),
):
    """Update a job application."""
    job = await get_job_or_404(db, job_id)

    update_data = job_data.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        if field == "status" and value:
            value = value.value if hasattr(value, "value") else value
        setattr(job, field, value)

    await db.flush()
    await db.refresh(job)

    return JobResponse.model_validate(job)


@router.delete("/{job_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_job(
    job_id: str,
    db: AsyncSession = Depends(get_db),
):
    from automation.orchestrator_manager import get_orchestrator_sync
    from automation.session_storage import session_storage
    
    job = await get_job_or_404(db, job_id)
    
    orchestrator = get_orchestrator_sync()
    if orchestrator:
        orchestrator.close_job_browser(job_id)
    
    session_storage.delete_session(job_id)
    
    await db.delete(job)


@router.post("/{job_id}/retry", response_model=JobResponse)
async def retry_job(
    job_id: str,
    db: AsyncSession = Depends(get_db),
):
    """Retry a failed job."""
    job = await get_job_or_404(db, job_id)

    if job.status not in [JobStatus.FAILED.value, JobStatus.CANCELLED.value]:
        raise HTTPException(status_code=400, detail="Only failed/cancelled jobs can be retried")

    job.status = JobStatus.PENDING.value
    job.retry_count += 1
    job.error_message = None
    job.started_at = None

    await db.flush()
    await db.refresh(job)

    return JobResponse.model_validate(job)


async def _process_jobs_parallel(job_ids: list[str], max_concurrent: int):
    from automation.notification_service import notification_service
    from app.database import async_session_maker
    from app.models.ai_settings import AISettings
    from app.models.profile import Profile
    from datetime import datetime
    import logging
    import sys
    import traceback
    logger = logging.getLogger(__name__)
    
    def notify_error(message: str, job_id: str = None):
        """Send error notification and print to console."""
        print(f"[ERROR] {message}", flush=True)
        sys.stdout.flush()
        try:
            notification_service.notify_error(
                job_id=job_id,
                error=message,
                title="Processing Error",
            )
        except Exception as e:
            print(f"[ERROR] Failed to send notification: {e}", flush=True)
    
    print("\n" + "="*70, flush=True)
    print(f"[PARALLEL] Starting processing of {len(job_ids)} jobs", flush=True)
    print(f"[PARALLEL] Max concurrent: {max_concurrent}", flush=True)
    print("="*70, flush=True)
    sys.stdout.flush()
    
    jobs = {}
    profiles_data = {}
    ai_settings = None
    
    try:
        # Load jobs and settings from database
        async with async_session_maker() as db:
            query = (
                select(JobApplication)
                .options(selectinload(JobApplication.profile))
                .where(JobApplication.id.in_(job_ids))
            )
            result = await db.execute(query)
            jobs = {str(j.id): j for j in result.scalars().all()}
            
            print(f"[PARALLEL] Loaded {len(jobs)} jobs from database", flush=True)
            
            for job in jobs.values():
                job.status = JobStatus.IN_PROGRESS.value
                job.started_at = datetime.utcnow()
            await db.commit()
            
            ai_settings = await db.scalar(select(AISettings).limit(1))
            
            profile_ids = set(j.profile_id for j in jobs.values())
            for pid in profile_ids:
                profile = await db.get(Profile, pid)
                if profile:
                    profiles_data[pid] = {
                        "id": profile.id,
                        "first_name": profile.first_name,
                        "middle_name": profile.middle_name,
                        "last_name": profile.last_name,
                        "email": profile.email,
                        "phone": profile.phone,
                        "address_1": profile.address_1,
                        "address_2": profile.address_2,
                        "city": profile.city,
                        "state": profile.state,
                        "country": profile.country,
                        "zip_code": profile.zip_code,
                        "linkedin_url": profile.linkedin_url,
                        "github_url": profile.github_url,
                        "portfolio_url": profile.portfolio_url,
                        "work_experience": profile.work_experience or [],
                        "education": profile.education or [],
                        "skills": profile.skills or [],
                    }
            
            print(f"[PARALLEL] Loaded {len(profiles_data)} profiles", flush=True)
    
    except Exception as e:
        error_msg = f"Failed to load jobs from database: {str(e)}"
        notify_error(error_msg)
        traceback.print_exc()
        return
    
    if not jobs:
        print("[PARALLEL] No valid jobs to process", flush=True)
        return
    
    # Get orchestrator
    try:
        from automation.orchestrator_manager import get_orchestrator
        
        browser_headless = ai_settings.browser_headless if ai_settings else False
        print(f"[PARALLEL] Browser headless mode: {browser_headless}", flush=True)
        print(f"[PARALLEL] API Key configured: {bool(ai_settings.openai_api_key) if ai_settings else False}", flush=True)
        sys.stdout.flush()
        
        orchestrator = await get_orchestrator(
            max_concurrent=max_concurrent,
            headless=browser_headless,
        )
        print(f"[PARALLEL] Orchestrator ready", flush=True)
        
        orchestrator.set_ai_service(
            api_key=ai_settings.openai_api_key,
            model=ai_settings.openai_model or "gpt-4o",
        )
        
        for profile_id, profile_data in profiles_data.items():
            orchestrator.set_profile_data(profile_id, profile_data)
        
        print(f"[PARALLEL] AI service and profiles configured", flush=True)
        sys.stdout.flush()
        
    except Exception as e:
        error_msg = f"Failed to initialize orchestrator: {str(e)}"
        notify_error(error_msg)
        traceback.print_exc()
        
        # Mark all jobs as failed
        async with async_session_maker() as db:
            for job_id in job_ids:
                job = await db.get(JobApplication, job_id)
                if job:
                    job.status = JobStatus.FAILED.value
                    job.error_message = error_msg[:500]
            await db.commit()
        return
    
    # Process jobs
    try:
        jobs_data = [
            (job_id, jobs[job_id].url, jobs[job_id].profile_id)
            for job_id in job_ids if job_id in jobs
        ]
        print(f"[PARALLEL] Jobs data prepared: {len(jobs_data)} jobs", flush=True)
        
        for jid, url, pid in jobs_data:
            print(f"  - {jid[:8]}: {url[:60]}...", flush=True)
        
        batches = [jobs_data[i:i + max_concurrent] for i in range(0, len(jobs_data), max_concurrent)]
        print(f"[PARALLEL] Created {len(batches)} batch(es)", flush=True)
        sys.stdout.flush()
        
        for batch_num, batch in enumerate(batches, 1):
            print(f"\n[BATCH {batch_num}/{len(batches)}] Processing {len(batch)} jobs...", flush=True)
            sys.stdout.flush()
            
            try:
                print(f"[BATCH {batch_num}] Calling orchestrator.process_jobs_with_autofill...", flush=True)
                sys.stdout.flush()
                
                results = await orchestrator.process_jobs_with_autofill(batch)
                print(f"[BATCH {batch_num}] Got {len(results)} results", flush=True)
                
                async with async_session_maker() as db:
                    for job_id, proc_result in results.items():
                        job = await db.get(JobApplication, job_id)
                        if job:
                            if proc_result.browser_kept_open:
                                job.status = JobStatus.AWAITING_ACTION.value
                                job.error_message = proc_result.fill_result.pause_reason if proc_result.fill_result else "Waiting for user action"
                            elif proc_result.success:
                                if proc_result.fill_result and proc_result.fill_result.submit_ready:
                                    job.status = JobStatus.APPLIED.value
                                else:
                                    job.status = JobStatus.IN_PROGRESS.value
                            else:
                                job.status = JobStatus.FAILED.value
                                job.error_message = (proc_result.error or "Unknown error")[:500]
                                notify_error(f"Job {job_id[:8]} failed: {proc_result.error}", job_id)
                            print(f"  [{job_id[:8]}] Status: {job.status}", flush=True)
                    await db.commit()
                
                print(f"[BATCH {batch_num}/{len(batches)}] Completed", flush=True)
                
            except Exception as e:
                error_msg = f"Batch {batch_num} error: {str(e)}"
                print(f"[BATCH ERROR] {error_msg}", flush=True)
                traceback.print_exc()
                sys.stdout.flush()
                notify_error(error_msg)
                
                # Mark batch jobs as failed
                async with async_session_maker() as db:
                    for job_id, url, pid in batch:
                        job = await db.get(JobApplication, job_id)
                        if job:
                            job.status = JobStatus.FAILED.value
                            job.error_message = error_msg[:500]
                    await db.commit()
        
        # Final status
        try:
            active_count = orchestrator.get_active_browsers_count()
            if active_count > 0:
                print(f"\n[PARALLEL] Completed. {active_count} browser(s) kept open.", flush=True)
            else:
                print("\n[PARALLEL] All jobs completed", flush=True)
        except Exception:
            pass
            
    except Exception as e:
        error_msg = f"Critical processing error: {str(e)}"
        print(f"[CRITICAL ERROR] {error_msg}", flush=True)
        traceback.print_exc()
        sys.stdout.flush()
        notify_error(error_msg)
        
        # Mark all jobs as failed
        try:
            async with async_session_maker() as db:
                for job_id in job_ids:
                    job = await db.get(JobApplication, job_id)
                    if job:
                        job.status = JobStatus.FAILED.value
                        job.error_message = error_msg[:500]
                await db.commit()
        except Exception:
            pass
    
    print("\n[PARALLEL] Processing function completed", flush=True)
    sys.stdout.flush()


@router.post("/start-processing", status_code=status.HTTP_202_ACCEPTED)
async def start_processing(
    profile_id: Optional[str] = None,
    limit: int = Query(10, ge=1, le=50),
    enable_autofill: bool = Query(True),
    include_failed: bool = Query(True),
    db: AsyncSession = Depends(get_db),
):
    from datetime import datetime, timedelta
    from sqlalchemy import or_
    from app.models.ai_settings import AISettings
    
    stuck_threshold = datetime.utcnow() - timedelta(minutes=5)
    
    # Build status conditions
    status_conditions = [
        JobApplication.status == JobStatus.PENDING.value,
        (JobApplication.status == JobStatus.QUEUED.value) & 
        (JobApplication.updated_at < stuck_threshold)
    ]
    
    # Include failed jobs if requested (for retry)
    if include_failed:
        status_conditions.append(JobApplication.status == JobStatus.FAILED.value)
    
    query = select(JobApplication).where(or_(*status_conditions))

    if profile_id:
        query = query.where(JobApplication.profile_id == profile_id)

    query = query.order_by(
        JobApplication.priority.desc(),
        JobApplication.created_at.asc(),
    ).limit(limit)

    result = await db.execute(query)
    jobs = result.scalars().all()
    
    print(f"[START] Found {len(jobs)} jobs to process", flush=True)

    if not jobs:
        return {
            "message": "No pending jobs to process",
            "queued": 0,
        }

    ai_settings = await db.scalar(select(AISettings).limit(1))
    max_concurrent = ai_settings.max_concurrent_jobs if ai_settings else 5
    
    has_api_key = ai_settings and ai_settings.openai_api_key
    
    if not has_api_key:
        raise HTTPException(
            status_code=400,
            detail="OpenAI API key is required for job processing. Please configure it in Settings."
        )

    job_ids = []
    for job in jobs:
        job.status = JobStatus.QUEUED.value
        job_ids.append(str(job.id))

    await db.commit()
    
    # Use asyncio.create_task for more reliable async task execution
    import asyncio
    asyncio.create_task(_process_jobs_parallel(job_ids, max_concurrent))
    
    print(f"[START] Background task created for {len(job_ids)} jobs", flush=True)

    return {
        "message": f"Queued {len(job_ids)} jobs for processing (max {max_concurrent} concurrent)",
        "queued": len(job_ids),
    }


@router.get("/{job_id}/session")
async def get_job_session(
    job_id: str,
    db: AsyncSession = Depends(get_db),
):
    from automation.session_storage import session_storage
    
    await get_job_or_404(db, job_id)
    
    session = session_storage.get_session(job_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    
    return session.to_dict()


@router.delete("/{job_id}/session", status_code=status.HTTP_204_NO_CONTENT)
async def delete_job_session(
    job_id: str,
    db: AsyncSession = Depends(get_db),
):
    from automation.session_storage import session_storage
    from automation.orchestrator_manager import get_orchestrator_sync
    
    await get_job_or_404(db, job_id)
    
    orchestrator = get_orchestrator_sync()
    if orchestrator:
        orchestrator.close_job_browser(job_id)
    
    session_storage.delete_session(job_id)


@router.get("/notifications/all")
async def get_all_notifications(
    limit: int = Query(50, ge=1, le=200),
    job_id: Optional[str] = None,
):
    from automation.notification_service import notification_service
    
    notifications = notification_service.get_notifications(limit=limit, job_id=job_id)
    return {
        "notifications": [n.to_dict() for n in notifications],
        "count": len(notifications),
    }


@router.get("/notifications/pending")
async def get_pending_notifications():
    from automation.notification_service import notification_service
    
    pending = notification_service.get_pending_actions()
    return {
        "notifications": [n.to_dict() for n in pending],
        "count": len(pending),
    }


@router.delete("/notifications/clear", status_code=status.HTTP_204_NO_CONTENT)
async def clear_notifications(
    job_id: Optional[str] = None,
):
    from automation.notification_service import notification_service
    
    notification_service.clear_notifications(job_id=job_id)


@router.post("/{job_id}/resume", response_model=JobResponse)
async def resume_job_after_captcha(
    job_id: str,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
):
    from automation.session_storage import session_storage
    from automation.orchestrator_manager import get_orchestrator_sync
    
    job = await get_job_or_404(db, job_id)
    
    if job.status != JobStatus.AWAITING_ACTION.value:
        raise HTTPException(
            status_code=400,
            detail=f"Job is not waiting for action. Current status: {job.status}"
        )
    
    session = session_storage.get_session(job_id)
    if not session:
        raise HTTPException(status_code=404, detail="No active session found for this job")
    
    orchestrator = get_orchestrator_sync()
    has_active_browser = orchestrator.has_active_browser(job_id) if orchestrator else False
    
    job.status = JobStatus.IN_PROGRESS.value
    job.error_message = None
    
    session_storage.set_session_status(job_id, "resuming", "User completed CAPTCHA, resuming...")
    
    await db.commit()
    await db.refresh(job)
    
    if has_active_browser and orchestrator:
        profile_id = job.profile_id
        
        async def resume_processing():
            from app.database import async_session_maker
            
            async with async_session_maker() as resume_db:
                profile = await resume_db.get(Profile, profile_id)
                if profile:
                    profile_data = {
                        "id": profile.id,
                        "first_name": profile.first_name,
                        "last_name": profile.last_name,
                        "email": profile.email,
                    }
                    orchestrator.set_profile_data(profile_id, profile_data)
                    result = orchestrator.resume_job_processing(job_id, profile_id)
                    
                    job_to_update = await resume_db.get(JobApplication, job_id)
                    if job_to_update and result:
                        if result.success and result.fill_result and result.fill_result.submit_ready:
                            job_to_update.status = JobStatus.APPLIED.value
                        elif result.captcha_detected or result.paused:
                            job_to_update.status = JobStatus.AWAITING_ACTION.value
                            job_to_update.error_message = result.fill_result.pause_reason if result.fill_result else None
                        elif result.success:
                            job_to_update.status = JobStatus.IN_PROGRESS.value
                        else:
                            job_to_update.status = JobStatus.FAILED.value
                            job_to_update.error_message = result.error
                        await resume_db.commit()
        
        background_tasks.add_task(resume_processing)
    
    return JobResponse.model_validate(job)


@router.get("/{job_id}/captcha-status")
async def get_captcha_status(
    job_id: str,
    db: AsyncSession = Depends(get_db),
):
    from automation.session_storage import session_storage
    from automation.orchestrator_manager import get_orchestrator_sync
    
    await get_job_or_404(db, job_id)
    
    session = session_storage.get_session(job_id)
    if not session:
        return {"has_captcha": False, "status": "no_session", "browser_active": False}
    
    is_captcha_waiting = session.status == "captcha_waiting"
    
    orchestrator = get_orchestrator_sync()
    browser_active = orchestrator.has_active_browser(job_id) if orchestrator else False
    
    return {
        "has_captcha": is_captcha_waiting,
        "status": session.status,
        "job_id": job_id,
        "current_page": session.current_page,
        "error_message": session.error_message,
        "browser_active": browser_active,
    }


@router.post("/{job_id}/close-browser")
async def close_job_browser(
    job_id: str,
    db: AsyncSession = Depends(get_db),
):
    from automation.orchestrator_manager import get_orchestrator_sync
    
    await get_job_or_404(db, job_id)
    
    orchestrator = get_orchestrator_sync()
    if not orchestrator:
        return {"success": False, "message": "No orchestrator running"}
    
    closed = orchestrator.close_job_browser(job_id)
    
    return {"success": closed, "message": "Browser closed" if closed else "No active browser found"}


@router.get("/{job_id}/history")
async def get_job_history(
    job_id: str,
    limit: int = Query(100, ge=1, le=500),
    db: AsyncSession = Depends(get_db),
):
    from automation.application_logger import application_logger
    
    await get_job_or_404(db, job_id)
    
    history = await application_logger.get_job_history(job_id, limit=limit)
    
    return {
        "job_id": job_id,
        "history": history,
        "count": len(history),
    }


@router.get("/{job_id}/summary")
async def get_job_summary(
    job_id: str,
    db: AsyncSession = Depends(get_db),
):
    from automation.application_logger import application_logger
    from automation.session_storage import session_storage
    
    job = await get_job_or_404(db, job_id)
    
    summary = await application_logger.get_job_summary(job_id)
    
    session = session_storage.get_session(job_id)
    session_data = None
    if session:
        session_data = {
            "status": session.status,
            "current_page": session.current_page,
            "pages_processed": len(session.page_snapshots),
            "autofill_results_count": len(session.autofill_results),
            "navigation_history": session.navigation_history,
            "created_at": session.created_at,
            "updated_at": session.updated_at,
            "error_message": session.error_message,
        }
    
    return {
        "job_id": job_id,
        "job_status": job.status,
        "job_url": job.url,
        "company_name": job.company_name,
        "job_title": job.job_title,
        "created_at": job.created_at.isoformat(),
        "updated_at": job.updated_at.isoformat(),
        "error_message": job.error_message,
        "summary": summary,
        "session": session_data,
    }


@router.get("/{job_id}/detail")
async def get_job_detail(
    job_id: str,
    db: AsyncSession = Depends(get_db),
):
    from automation.application_logger import application_logger
    from automation.session_storage import session_storage
    
    job = await get_job_or_404(db, job_id)
    
    history = await application_logger.get_job_history(job_id, limit=200)
    
    session = session_storage.get_session(job_id)
    
    autofill_results = []
    page_snapshots = []
    if session:
        autofill_results = [
            {
                "field_name": r.field_name,
                "selector": r.selector,
                "action": r.action,
                "success": r.success,
                "error": r.error,
            }
            for r in session.autofill_results
        ]
        
        page_snapshots = [
            {
                "url": s.url,
                "title": s.title,
                "page_number": s.page_number,
                "inputs_count": len(s.inputs),
                "buttons_count": len(s.buttons),
                "timestamp": s.timestamp,
            }
            for s in session.page_snapshots
        ]
    
    profile = await db.get(Profile, job.profile_id)
    profile_name = f"{profile.first_name} {profile.last_name}" if profile else "Unknown"
    
    return {
        "job": {
            "id": job.id,
            "url": job.url,
            "company_name": job.company_name,
            "job_title": job.job_title,
            "location": job.location,
            "status": job.status,
            "error_message": job.error_message,
            "retry_count": job.retry_count,
            "profile_id": job.profile_id,
            "profile_name": profile_name,
            "created_at": job.created_at.isoformat(),
            "updated_at": job.updated_at.isoformat(),
            "started_at": job.started_at.isoformat() if job.started_at else None,
            "applied_at": job.applied_at.isoformat() if job.applied_at else None,
        },
        "history": history,
        "autofill_results": autofill_results,
        "page_snapshots": page_snapshots,
    }
