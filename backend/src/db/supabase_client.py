"""Sync Supabase client. The agent wraps calls in asyncio.to_thread."""

from supabase import Client, create_client

from src.config import settings

_supabase: Client | None = None


def get_supabase() -> Client:
    global _supabase
    if _supabase is None:
        if not settings.supabase_url or not settings.supabase_key:
            raise RuntimeError("SUPABASE_URL and SUPABASE_KEY must be set")
        _supabase = create_client(settings.supabase_url, settings.supabase_key)
    return _supabase
