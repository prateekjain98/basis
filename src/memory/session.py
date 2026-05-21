"""
Session memory manager.
In-memory only for PS3 scope. Production would add Redis/SQLite persistence.
"""

from __future__ import annotations

import uuid
from typing import Dict, Optional

from src.models.schemas import ResearchPrompt, SessionState


class SessionManager:
    """Keeps track of all active research sessions."""

    def __init__(self) -> None:
        self._sessions: Dict[str, SessionState] = {}

    def create_session(self, prompt: ResearchPrompt) -> str:
        """Start a new research session. Returns session_id."""
        session_id = str(uuid.uuid4())[:8]
        self._sessions[session_id] = SessionState(
            session_id=session_id,
            original_prompt=prompt,
        )
        return session_id

    def get_session(self, session_id: str) -> Optional[SessionState]:
        """Retrieve an existing session."""
        return self._sessions.get(session_id)

    def update_session(self, session_id: str, state: SessionState) -> None:
        """Overwrite session state after a turn."""
        self._sessions[session_id] = state

    def list_sessions(self) -> list[str]:
        """Debug helper — list active session IDs."""
        return list(self._sessions.keys())


# Global singleton — in-memory only
_session_manager: Optional[SessionManager] = None


def get_session_manager() -> SessionManager:
    """Lazy-initialized singleton so we don't reset between turns."""
    global _session_manager
    if _session_manager is None:
        _session_manager = SessionManager()
    return _session_manager
