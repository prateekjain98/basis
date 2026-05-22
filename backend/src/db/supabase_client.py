"""Supabase client with in-memory fallback for demo / missing credentials."""

from __future__ import annotations

import os
from typing import Any

from src.config import settings


class _InMemoryTable:
    """Simple in-memory table for fallback mode."""

    def __init__(self) -> None:
        self._rows: list[dict] = []

    def select(self, *cols: str) -> "_InMemoryQuery":
        return _InMemoryQuery(self)

    def insert(self, data: dict | list) -> "_InMemoryAction":
        if isinstance(data, dict):
            data = [data]
        self._rows.extend(data)
        return _InMemoryAction(data)

    def update(self, data: dict) -> "_InMemoryQuery":
        return _InMemoryQuery(self, update_data=data)

    def delete(self) -> "_InMemoryQuery":
        return _InMemoryQuery(self, delete=True)


class _InMemoryQuery:
    def __init__(self, table: _InMemoryTable, update_data: dict | None = None, delete: bool = False) -> None:
        self._table = table
        self._rows = list(table._rows)
        self._update_data = update_data
        self._delete = delete
        self._filters: list = []

    def eq(self, column: str, value: Any) -> "_InMemoryQuery":
        self._filters.append((column, value))
        return self

    def order(self, column: str, desc: bool = False) -> "_InMemoryQuery":
        self._rows.sort(key=lambda r: r.get(column), reverse=desc)
        return self

    def execute(self) -> Any:
        result = self._rows
        for col, val in self._filters:
            result = [r for r in result if r.get(col) == val]

        if self._delete:
            for r in result:
                if r in self._table._rows:
                    self._table._rows.remove(r)
            return _MockResponse([{"deleted": True}])

        if self._update_data:
            for r in result:
                r.update(self._update_data)
            return _MockResponse(result)

        return _MockResponse(result)


class _InMemoryAction:
    def __init__(self, data: list) -> None:
        self._data = data

    def execute(self) -> Any:
        return _MockResponse(self._data)


class _MockResponse:
    def __init__(self, data: list) -> None:
        self.data = data


class _InMemoryDB:
    """In-memory database with Supabase-like API."""

    def __init__(self) -> None:
        self._tables: dict[str, _InMemoryTable] = {}

    def table(self, name: str) -> _InMemoryTable:
        if name not in self._tables:
            self._tables[name] = _InMemoryTable()
        return self._tables[name]


_supabase: Any | None = None
_db: _InMemoryDB | None = None


def get_supabase() -> Any:
    global _supabase, _db
    if _supabase is not None:
        return _supabase

    force_supabase = os.getenv("FORCE_SUPABASE", "").lower() in ("1", "true", "yes")

    if settings.supabase_url and settings.supabase_key:
        try:
            from supabase import create_client
            client = create_client(settings.supabase_url, settings.supabase_key)
            # Quick health check
            client.table("thesis_sessions").select("*").limit(1).execute()
            _supabase = client
            print("[Supabase] Connected to remote")
            return _supabase
        except Exception as e:
            if force_supabase:
                raise RuntimeError(f"FORCE_SUPABASE is set but connection failed: {e}") from e
            print(f"[Supabase] Remote connection failed ({e}), using in-memory fallback")

    if _db is None:
        _db = _InMemoryDB()
        print("[Supabase] Using in-memory fallback")
    return _db
