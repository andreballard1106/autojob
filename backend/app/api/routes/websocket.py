"""
WebSocket Route for Real-time Updates

Provides live job status updates to connected clients.
"""

import asyncio
import json
import logging
from typing import Set

from fastapi import APIRouter, WebSocket, WebSocketDisconnect

logger = logging.getLogger(__name__)

router = APIRouter()

# Connected WebSocket clients
_clients: Set[WebSocket] = set()


@router.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    """WebSocket endpoint for real-time job updates."""
    await websocket.accept()
    _clients.add(websocket)
    logger.info(f"WebSocket client connected. Total clients: {len(_clients)}")

    try:
        # Send initial connection message
        await websocket.send_json({
            "type": "connected",
            "message": "Connected to Job Application System",
        })

        # Keep connection alive and handle incoming messages
        while True:
            try:
                # Wait for messages (ping/pong or commands)
                data = await asyncio.wait_for(websocket.receive_text(), timeout=30)

                # Handle ping
                if data == "ping":
                    await websocket.send_text("pong")
                else:
                    # Echo for debugging
                    logger.debug(f"WebSocket received: {data}")

            except asyncio.TimeoutError:
                # Send ping to keep connection alive
                await websocket.send_text("ping")

    except WebSocketDisconnect:
        logger.info("WebSocket client disconnected")
    except Exception as e:
        logger.error(f"WebSocket error: {e}")
    finally:
        _clients.discard(websocket)
        logger.info(f"WebSocket client removed. Remaining clients: {len(_clients)}")


async def broadcast(message: dict) -> None:
    """Broadcast a message to all connected clients."""
    if not _clients:
        return

    disconnected = set()
    for client in _clients:
        try:
            await client.send_json(message)
        except Exception as e:
            logger.warning(f"Failed to send to client: {e}")
            disconnected.add(client)

    # Remove disconnected clients
    for client in disconnected:
        _clients.discard(client)


# Helper functions for specific event types

async def emit_job_status_changed(
    job_id: str,
    profile_id: str,
    old_status: str,
    new_status: str,
    job_title: str = None,
    company_name: str = None,
) -> None:
    """Emit job status change event."""
    await broadcast({
        "type": "job_status_changed",
        "job_id": job_id,
        "profile_id": profile_id,
        "old_status": old_status,
        "new_status": new_status,
        "job_title": job_title,
        "company_name": company_name,
    })


async def emit_job_completed(
    job_id: str,
    profile_id: str,
    job_title: str = None,
    company_name: str = None,
    confirmation_ref: str = None,
) -> None:
    """Emit job completion event."""
    await broadcast({
        "type": "job_completed",
        "job_id": job_id,
        "profile_id": profile_id,
        "job_title": job_title,
        "company_name": company_name,
        "confirmation_ref": confirmation_ref,
    })


async def emit_intervention_needed(
    job_id: str,
    profile_id: str,
    challenge_type: str,
    message: str,
    job_title: str = None,
    company_name: str = None,
) -> None:
    """Emit intervention needed event."""
    await broadcast({
        "type": "intervention_needed",
        "job_id": job_id,
        "profile_id": profile_id,
        "challenge_type": challenge_type,
        "message": message,
        "job_title": job_title,
        "company_name": company_name,
    })


async def emit_log(
    job_id: str,
    action: str,
    details: dict = None,
) -> None:
    """Emit log event."""
    await broadcast({
        "type": "log",
        "job_id": job_id,
        "action": action,
        "details": details,
    })
