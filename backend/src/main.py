"""FastAPI entry point."""

from __future__ import annotations

import asyncio
import os
from typing import AsyncIterator, List, Optional

from dotenv import load_dotenv
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

from src.agent import Agent
from src.config import settings
from src.db.supabase_client import get_supabase
from src.tools.vector_store import SessionVectorStore

load_dotenv()

app = FastAPI(title="Basis Agent API")
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",
        "http://localhost:3001",
        "https://meraki.prateekjain.io",
        "https://*.vercel.app",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

agent = Agent()


class ChatRequest(BaseModel):
    messages: List[dict]
    session_id: Optional[str] = None
    model: Optional[str] = None


@app.post("/chat")
async def chat(req: ChatRequest) -> StreamingResponse:
    user_msgs = [m for m in req.messages if m.get("role") == "user"]
    if not user_msgs:
        return StreamingResponse(iter(["No user message."]), media_type="text/plain")

    query = user_msgs[-1].get("content", "")

    async def generate() -> AsyncIterator[str]:
        async for chunk in agent.run(query, session_id=req.session_id, history=req.messages, model=req.model):
            yield chunk

    return StreamingResponse(generate(), media_type="text/plain")


@app.get("/sessions")
async def list_sessions() -> List[dict]:
    try:
        db = get_supabase()
        resp = await asyncio.to_thread(
            db.table("thesis_sessions").select("*").order("created_at", desc=True).execute
        )
        return [
            {
                "id": s["id"],
                "title": (s.get("theme") or s["user_query"])[:50] + "..."
                if len(s.get("theme") or s["user_query"]) > 50
                else (s.get("theme") or s["user_query"]),
                "conviction": s.get("conviction"),
                "created_at": s.get("created_at"),
            }
            for s in resp.data
        ]
    except Exception as e:
        print(f"[API] list_sessions error: {e}")
        return []


@app.get("/sessions/{session_id}")
async def get_session(session_id: str) -> dict:
    try:
        db = get_supabase()
        t = (await asyncio.to_thread(
            db.table("thesis_sessions").select("*").eq("id", session_id).execute
        )).data
        if not t:
            return {"error": "not found"}
        s = t[0]
        stocks = (await asyncio.to_thread(
            db.table("stock_recommendations").select("*").eq("thesis_id", session_id).execute
        )).data
        docs = (await asyncio.to_thread(
            db.table("documents").select("*").eq("thesis_id", session_id).execute
        )).data
        msgs = (await asyncio.to_thread(
            db.table("messages").select("*").eq("session_id", session_id).order("created_at").execute
        )).data
        return {
            "id": s["id"],
            "theme": s.get("theme"),
            "user_query": s["user_query"],
            "summary": s.get("summary"),
            "conviction": s.get("conviction"),
            "created_at": s.get("created_at"),
            "stocks": [{"ticker": st["ticker"], "name": st.get("name"), "entry_price": st.get("entry_price"),
                        "total_score": st.get("total_score"), "rationale": st.get("rationale")} for st in stocks],
            "documents": [{"url": d["url"], "title": d.get("title"), "chunk_count": d.get("chunk_count", 0)} for d in docs],
            "messages": [{"role": m["role"], "content": m["content"]} for m in msgs],
        }
    except Exception as e:
        print(f"[API] get_session error: {e}")
        return {"error": "server error"}


@app.delete("/sessions/{session_id}")
async def delete_session(session_id: str) -> dict:
    try:
        db = get_supabase()
        await asyncio.to_thread(
            db.table("thesis_sessions").delete().eq("id", session_id).execute
        )
    except Exception as e:
        print(f"[API] delete_session error: {e}")
    SessionVectorStore().delete_session(session_id)
    return {"deleted": session_id}


@app.get("/models")
async def list_models() -> dict:
    """Return available models based on configured API keys."""
    available = []
    default = None

    if settings.vertex_project:
        available.extend([
            "gemini-2.0-flash-001",
            "gemini-2.5-pro-preview-03-25",
            "gemini-2.0-flash-lite-001",
        ])
        default = settings.vertex_model or "gemini-2.0-flash-001"

    if settings.anthropic_api_key:
        available.extend([
            "claude-3-5-haiku-20241022",
            "claude-3-5-sonnet-20241022",
            "claude-3-opus-20240229",
        ])
        if not default:
            default = settings.anthropic_model or "claude-3-5-haiku-20241022"

    if settings.openai_api_key:
        available.extend([
            "gpt-4o-mini",
            "gpt-4o",
            "o3-mini",
            "o1",
        ])
        if not default:
            default = settings.llm_model or "gpt-4o-mini"

    return {
        "available_models": available,
        "default_model": default or "gpt-4o-mini",
        "providers": {
            "openai": bool(settings.openai_api_key),
            "anthropic": bool(settings.anthropic_api_key),
            "google": bool(settings.vertex_project),
        },
    }


@app.get("/health")
async def health() -> dict:
    return {"status": "ok"}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("src.main:app", host="0.0.0.0", port=int(os.getenv("PORT", "8000")), reload=True)
