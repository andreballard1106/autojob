"""
AI Settings API Routes
"""

from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models.ai_settings import AISettings, DEFAULT_QUESTION_PROMPTS, DEFAULT_FORM_ANSWERS
from app.schemas.ai_settings import (
    AISettingsUpdate,
    AISettingsPublicResponse,
    DEFAULT_QUESTION_PROMPTS_LIST,
    DEFAULT_FORM_FIELDS_LIST,
)
from app.api.helpers import build_ai_settings_response

router = APIRouter()


def mask_api_key(api_key: str | None) -> str | None:
    """Mask API key for display, showing only first and last 4 characters."""
    if not api_key or len(api_key) < 12:
        return "••••••••" if api_key else None
    return f"{api_key[:4]}••••••••{api_key[-4:]}"


async def get_or_create_settings(db: AsyncSession) -> AISettings:
    """Get existing settings or create default ones."""
    result = await db.execute(select(AISettings).limit(1))
    settings = result.scalar_one_or_none()
    
    if not settings:
        settings = AISettings(
            openai_model="gpt-4o",
            temperature=0.7,
            max_tokens=2000,
            resume_tone="professional",
            resume_format="bullet",
            resume_max_pages=2,
            cover_letter_tone="professional",
            cover_letter_length="medium",
            question_prompts=DEFAULT_QUESTION_PROMPTS,
            default_answers=DEFAULT_FORM_ANSWERS,
            max_concurrent_jobs=5,
            browser_timeout=300,
            browser_headless=False,
            screenshot_on_error=True,
            auto_retry_failed=True,
            max_retries=3,
            ai_timeout_seconds=60,
            use_fallback_on_error=True,
        )
        db.add(settings)
        await db.flush()
        await db.refresh(settings)
    
    return settings


@router.get("", response_model=AISettingsPublicResponse)
async def get_ai_settings(
    db: AsyncSession = Depends(get_db),
):
    """Get current AI settings (with masked API key)."""
    settings = await get_or_create_settings(db)
    return build_ai_settings_response(settings)


@router.put("", response_model=AISettingsPublicResponse)
async def update_ai_settings(
    settings_data: AISettingsUpdate,
    db: AsyncSession = Depends(get_db),
):
    """Update AI settings."""
    settings = await get_or_create_settings(db)
    
    update_data = settings_data.model_dump(exclude_unset=True)
    
    for field, value in update_data.items():
        setattr(settings, field, value)
    
    await db.flush()
    await db.refresh(settings)
    
    return build_ai_settings_response(settings)


@router.get("/defaults")
async def get_default_prompts():
    """Get default prompt templates and form field definitions."""
    return {
        "question_prompts": DEFAULT_QUESTION_PROMPTS,
        "question_prompts_list": DEFAULT_QUESTION_PROMPTS_LIST,
        "default_answers": DEFAULT_FORM_ANSWERS,
        "form_fields_list": DEFAULT_FORM_FIELDS_LIST,
    }


@router.post("/reset-prompts")
async def reset_prompts_to_defaults(
    db: AsyncSession = Depends(get_db),
):
    """Reset all prompts to default values."""
    settings = await get_or_create_settings(db)
    
    settings.question_prompts = DEFAULT_QUESTION_PROMPTS
    settings.default_answers = DEFAULT_FORM_ANSWERS
    
    await db.flush()
    await db.refresh(settings)
    
    return {"message": "Prompts reset to defaults", "success": True}


@router.post("/test-connection")
async def test_ai_connection(
    db: AsyncSession = Depends(get_db),
):
    """Test the OpenAI API connection and fetch available models."""
    settings = await get_or_create_settings(db)
    
    if not settings.openai_api_key:
        return {
            "success": False,
            "message": "No API key configured",
            "models": [],
        }
    
    try:
        from openai import OpenAI
        
        client = OpenAI(api_key=settings.openai_api_key)
        
        # Fetch available models from OpenAI
        models_response = client.models.list()
        
        # Filter to only include GPT chat models (exclude embeddings, whisper, dall-e, etc.)
        chat_model_prefixes = ("gpt-4", "gpt-3.5", "o1", "o3")
        excluded_keywords = ("instruct", "vision", "audio", "realtime")
        
        available_models = []
        for model in models_response.data:
            model_id = model.id.lower()
            # Include only chat models
            if any(model_id.startswith(prefix) for prefix in chat_model_prefixes):
                # Exclude non-chat variants
                if not any(kw in model_id for kw in excluded_keywords):
                    available_models.append({
                        "id": model.id,
                        "name": model.id,
                        "created": model.created,
                    })
        
        # Sort by creation date (newest first) and then by name
        available_models.sort(key=lambda x: (-x.get("created", 0), x["id"]))
        
        # Save available models to database
        settings.available_models = available_models
        await db.flush()
        await db.refresh(settings)
        
        # Test with a simple API call using the current model or first available
        test_model = settings.openai_model
        if available_models and test_model not in [m["id"] for m in available_models]:
            test_model = available_models[0]["id"]
        
        response = client.chat.completions.create(
            model=test_model,
            messages=[{"role": "user", "content": "Say 'OK'"}],
            max_tokens=5,
        )
        
        return {
            "success": True,
            "message": f"API connection successful. Found {len(available_models)} available models.",
            "model": test_model,
            "response": response.choices[0].message.content,
            "models": available_models,
        }
        
    except Exception as e:
        return {
            "success": False,
            "message": str(e),
            "models": [],
        }

