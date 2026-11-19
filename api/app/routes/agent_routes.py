from typing import List, Dict, Optional, Any
from fastapi import APIRouter, HTTPException, Request, status
from pydantic import BaseModel, Field
from app.services.agent_service import agent_service

router = APIRouter(prefix="/agent", tags=["AI Assistant"])

class ChatMessage(BaseModel):
    role: str
    content: str

class AgentChatRequest(BaseModel):
    message: str = Field(..., min_length=1, max_length=1500)
    history: Optional[List[ChatMessage]] = []

class AgentChatResponse(BaseModel):
    reply: str
    language: str

# Simple in-memory sliding window rate limiter for agent endpoint
IP_AGENT_TIMESTAMPS: Dict[str, List[float]] = {}
AGENT_RATE_LIMIT = 25  # max 25 calls per minute per IP
WINDOW_SECONDS = 60

@router.post("/chat", response_model=AgentChatResponse)
def agent_chat(req_data: AgentChatRequest, request: Request):
    client_ip = request.client.host if request.client else "unknown"
    import time
    now = time.time()
    
    # Check rate limit
    timestamps = IP_AGENT_TIMESTAMPS.get(client_ip, [])
    timestamps = [t for t in timestamps if now - t < WINDOW_SECONDS]
    if len(timestamps) >= AGENT_RATE_LIMIT:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Too many queries to the assistant. Please wait a minute before asking again."
        )
    timestamps.append(now)
    IP_AGENT_TIMESTAMPS[client_ip] = timestamps

    hist_dicts = [{"role": m.role, "content": m.content} for m in req_data.history or []]
    result = agent_service.chat(message=req_data.message, history=hist_dicts)
    
    return AgentChatResponse(
        reply=result.get("reply", ""),
        language=result.get("language", "English")
    )
