"""Document parser with LlamaParse primary + PyMuPDF fallback."""

from __future__ import annotations

from typing import Optional

from src.config import settings


class DocumentParser:
    def __init__(self) -> None:
        key = settings.llama_cloud_api_key
        self._llama = None
        if key:
            try:
                from llama_parse import LlamaParse
                self._llama = LlamaParse(api_key=key, result_type="markdown")
            except Exception as e:
                print(f"[DocumentParser] LlamaParse init failed: {e}")

    def parse(self, file_path: str) -> Optional[str]:
        # Try LlamaParse first if available
        if self._llama is not None:
            try:
                docs = self._llama.load_data(file_path)
                text = "\n\n".join(d.text for d in docs if d.text)
                if text and len(text.strip()) > 100:
                    return text
            except Exception as e:
                print(f"[DocumentParser] LlamaParse failed: {e}")

        # Fallback to PyMuPDF
        try:
            import fitz  # PyMuPDF
            doc = fitz.open(file_path)
            parts = []
            for page in doc:
                txt = page.get_text()
                if txt.strip():
                    parts.append(txt)
            doc.close()
            text = "\n\n".join(parts)
            if text and len(text.strip()) > 100:
                return text
        except Exception as e:
            print(f"[DocumentParser] PyMuPDF failed: {e}")

        return None
