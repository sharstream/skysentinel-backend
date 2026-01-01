"""
Session Manager API
Simple session management with enable/disable toggle for AI features

Manages AI agent sessions with encrypted API key storage and
MCP connection state. Uses in-memory storage for development,
Redis recommended for production.
"""
from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel
from typing import Optional, Dict
import uuid
from datetime import datetime

router = APIRouter(prefix="/api/v1/ai-session", tags=["AI Session"])


class SessionConfig(BaseModel):
    """AI agent session configuration"""
    session_id: str
    enabled: bool
    active_provider: str  # 'openai', 'anthropic', 'google'
    api_key_hash: str  # Encrypted API key identifier (not the actual key)
    context_preferences: Dict = {}
    created_at: str
    last_active: str


class SessionCreateRequest(BaseModel):
    """Request to create new AI session"""
    provider: str
    encrypted_api_key: str


class SessionToggleRequest(BaseModel):
    """Request to enable/disable session"""
    enabled: bool


# In-memory session store
# TODO: Replace with Redis for production deployment
_sessions: Dict[str, SessionConfig] = {}


@router.post("/create", status_code=status.HTTP_201_CREATED)
async def create_session(request: SessionCreateRequest):
    """
    Create new AI agent session
    
    Args:
        request: Session creation request with provider and encrypted API key
    
    Returns:
        Session ID and creation status
    """
    try:
        session_id = str(uuid.uuid4())
        now = datetime.utcnow().isoformat()
        
        _sessions[session_id] = SessionConfig(
            session_id=session_id,
            enabled=True,
            active_provider=request.provider,
            api_key_hash=request.encrypted_api_key,
            created_at=now,
            last_active=now
        )
        
        print(f"✓ AI session created: {session_id} (provider: {request.provider})")
        
        return {
            "session_id": session_id,
            "status": "created",
            "provider": request.provider
        }
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create session: {str(e)}"
        )


@router.post("/{session_id}/toggle")
async def toggle_session(session_id: str, request: SessionToggleRequest):
    """
    Enable/disable AI features for this session
    
    Args:
        session_id: Session identifier
        request: Toggle request with enabled flag
    
    Returns:
        Updated session status
    """
    if session_id not in _sessions:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Session not found"
        )
    
    _sessions[session_id].enabled = request.enabled
    _sessions[session_id].last_active = datetime.utcnow().isoformat()
    
    action = "enabled" if request.enabled else "disabled"
    print(f"✓ AI session {session_id} {action}")
    
    return {
        "session_id": session_id,
        "enabled": request.enabled,
        "status": "updated"
    }


@router.get("/{session_id}")
async def get_session(session_id: str):
    """
    Get session configuration
    
    Args:
        session_id: Session identifier
    
    Returns:
        Session configuration (without API key)
    """
    if session_id not in _sessions:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Session not found"
        )
    
    session = _sessions[session_id]
    
    # Update last active timestamp
    session.last_active = datetime.utcnow().isoformat()
    
    return {
        "session_id": session.session_id,
        "enabled": session.enabled,
        "active_provider": session.active_provider,
        "created_at": session.created_at,
        "last_active": session.last_active,
        "context_preferences": session.context_preferences
    }


@router.delete("/{session_id}")
async def delete_session(session_id: str):
    """
    Delete AI session
    
    Args:
        session_id: Session identifier
    
    Returns:
        Deletion confirmation
    """
    if session_id not in _sessions:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Session not found"
        )
    
    del _sessions[session_id]
    print(f"✓ AI session deleted: {session_id}")
    
    return {
        "session_id": session_id,
        "status": "deleted"
    }


@router.get("/")
async def list_sessions():
    """
    List all active sessions (for debugging)
    
    Returns:
        List of active session IDs
    """
    return {
        "sessions": [
            {
                "session_id": s.session_id,
                "enabled": s.enabled,
                "provider": s.active_provider,
                "created_at": s.created_at
            }
            for s in _sessions.values()
        ],
        "total": len(_sessions)
    }


def is_session_valid(session_id: str) -> bool:
    """
    Check if session exists and is enabled
    
    Args:
        session_id: Session identifier
    
    Returns:
        True if session is valid and enabled
    """
    session = _sessions.get(session_id)
    return session is not None and session.enabled


def get_session_provider(session_id: str) -> Optional[str]:
    """
    Get active provider for session
    
    Args:
        session_id: Session identifier
    
    Returns:
        Provider name or None if session not found
    """
    session = _sessions.get(session_id)
    return session.active_provider if session else None

