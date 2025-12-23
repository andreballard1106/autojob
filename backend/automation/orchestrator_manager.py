import asyncio
import logging
import sys
from typing import Optional

from automation.ai_orchestrator import AIOrchestrator

logger = logging.getLogger(__name__)

_orchestrator: Optional[AIOrchestrator] = None
_initialized = False


async def get_orchestrator(
    max_concurrent: int = None,
    headless: bool = None,
) -> AIOrchestrator:
    """Get or create the orchestrator singleton."""
    global _orchestrator, _initialized
    
    print(f"[ORCHESTRATOR_MGR] get_orchestrator called (max={max_concurrent}, headless={headless})", flush=True)
    sys.stdout.flush()
    
    if _orchestrator is None:
        print(f"[ORCHESTRATOR_MGR] Creating NEW orchestrator instance...", flush=True)
        sys.stdout.flush()
        try:
            _orchestrator = AIOrchestrator(max_concurrent=max_concurrent, headless=headless)
            print(f"[ORCHESTRATOR_MGR] Orchestrator created successfully", flush=True)
        except Exception as e:
            print(f"[ORCHESTRATOR_MGR ERROR] Failed to create orchestrator: {e}", flush=True)
            import traceback
            traceback.print_exc()
            sys.stdout.flush()
            raise
    elif headless is not None:
        print(f"[ORCHESTRATOR_MGR] Updating headless setting to: {headless}", flush=True)
        _orchestrator.set_headless(headless)
    
    if not _initialized:
        print(f"[ORCHESTRATOR_MGR] Initializing orchestrator...", flush=True)
        sys.stdout.flush()
        try:
            await _orchestrator.initialize()
            _initialized = True
            print(f"[ORCHESTRATOR_MGR] Orchestrator initialized successfully", flush=True)
        except Exception as e:
            print(f"[ORCHESTRATOR_MGR ERROR] Failed to initialize: {e}", flush=True)
            import traceback
            traceback.print_exc()
            sys.stdout.flush()
            raise
    
    sys.stdout.flush()
    return _orchestrator


def get_orchestrator_sync() -> Optional[AIOrchestrator]:
    return _orchestrator


async def shutdown_orchestrator():
    global _orchestrator, _initialized
    
    if _orchestrator:
        await _orchestrator.shutdown()
        _orchestrator = None
        _initialized = False


def is_orchestrator_running() -> bool:
    return _initialized and _orchestrator is not None

