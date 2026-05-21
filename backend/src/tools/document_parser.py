"""LlamaParse wrapper. Falls back to None if no API key."""

from __future__ import annotations

from typing import Optional

from llama_parse import LlamaParse

from src.config import settings


class DocumentParser:
    def __init__(self) -> None:
        key = settings.llama_cloud_api_key
        self.parser = LlamaParse(api_key=key, result_type="markdown") if key else None

    def parse(self, file_path: str) -> Optional[str]:
        if self.parser is None:
            return None
        try:
            docs = self.parser.load_data(file_path)
            return "\n\n".join(d.text for d in docs if d.text)
        except Exception as e:
            print(f"[DocumentParser] failed: {e}")
            return None
