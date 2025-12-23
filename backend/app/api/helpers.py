from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.profile import Profile
from app.models.job import JobApplication
from app.models.ai_settings import AISettings


async def get_profile_or_404(db: AsyncSession, profile_id: str) -> Profile:
    profile = await db.get(Profile, profile_id)
    if not profile:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Profile not found",
        )
    return profile


async def get_job_or_404(db: AsyncSession, job_id: str) -> JobApplication:
    job = await db.get(JobApplication, job_id)
    if not job:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Job not found",
        )
    return job


async def get_application_or_404(db: AsyncSession, application_id: str) -> JobApplication:
    application = await db.get(JobApplication, application_id)
    if not application:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Application not found",
        )
    return application


def validate_work_experience_index(work_experience: list, index: int) -> None:
    if index < 0 or index >= len(work_experience):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Work experience index {index} out of range",
        )


def build_ai_settings_response(settings: AISettings):
    from app.schemas.ai_settings import AISettingsPublicResponse
    from app.api.routes.ai_settings import mask_api_key
    
    return AISettingsPublicResponse(
        id=settings.id,
        openai_api_key_masked=mask_api_key(settings.openai_api_key),
        openai_model=settings.openai_model,
        temperature=settings.temperature,
        max_tokens=settings.max_tokens,
        available_models=settings.available_models or [],
        enable_resume_generation=settings.enable_resume_generation,
        enable_cover_letter_generation=settings.enable_cover_letter_generation,
        enable_answer_generation=settings.enable_answer_generation,
        resume_system_prompt=settings.resume_system_prompt,
        resume_tone=settings.resume_tone,
        resume_format=settings.resume_format,
        resume_max_pages=settings.resume_max_pages,
        cover_letter_system_prompt=settings.cover_letter_system_prompt,
        cover_letter_tone=settings.cover_letter_tone,
        cover_letter_length=settings.cover_letter_length,
        question_prompts=settings.question_prompts or {},
        default_answers=settings.default_answers or {},
        max_concurrent_jobs=settings.max_concurrent_jobs,
        browser_timeout=settings.browser_timeout,
        browser_headless=settings.browser_headless,
        screenshot_on_error=settings.screenshot_on_error,
        auto_retry_failed=settings.auto_retry_failed,
        max_retries=settings.max_retries,
        ai_timeout_seconds=settings.ai_timeout_seconds,
        use_fallback_on_error=settings.use_fallback_on_error,
        created_at=settings.created_at,
        updated_at=settings.updated_at,
    )

