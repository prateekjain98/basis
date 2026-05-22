"""Vector store with Qdrant primary + Supabase fallback + in-memory dev fallback."""

from __future__ import annotations

import hashlib
from typing import List, Optional

from llama_index.core import Document, Settings, StorageContext, VectorStoreIndex
from llama_index.core.node_parser import SentenceSplitter
from llama_index.embeddings.openai import OpenAIEmbedding
from llama_index.embeddings.ollama import OllamaEmbedding
from llama_index.vector_stores.qdrant import QdrantVectorStore
from qdrant_client import QdrantClient

from src.config import settings
from src.db.supabase_client import get_supabase


class SessionVectorStore:
    """Per-session vector index. Falls back to Supabase (cloud) or in-memory (dev)."""

    def __init__(self) -> None:
        self._qdrant: Optional[QdrantClient] = None
        self._fallback: dict[str, list[str]] = {}
        self._init_qdrant()

    def _init_qdrant(self) -> None:
        if not settings.qdrant_url or settings.qdrant_url == "http://localhost:6333":
            return
        try:
            kwargs = {"url": settings.qdrant_url, "timeout": 10}
            if settings.qdrant_api_key:
                kwargs["api_key"] = settings.qdrant_api_key
            self._qdrant = QdrantClient(**kwargs)
            self._qdrant.get_collections()
        except Exception as e:
            print(f"[VectorStore] Qdrant unavailable ({e}), using Supabase fallback")
            self._qdrant = None

    def index_documents(self, session_id: str, texts: List[str]) -> int:
        if not texts:
            return 0

        if self._qdrant is not None:
            try:
                return self._index_qdrant(session_id, texts)
            except Exception as e:
                print(f"[VectorStore] Qdrant index failed ({e}), falling back to Supabase")

        return self._index_supabase(session_id, texts)

    def _get_embed_model(self):
        if "localhost:11434" in settings.openai_base_url or "127.0.0.1:11434" in settings.openai_base_url:
            return OllamaEmbedding(
                model_name="nomic-embed-text",
                base_url=settings.openai_base_url.replace("/v1", ""),
            )
        return OpenAIEmbedding(
            api_key=settings.openai_api_key or "dummy",
            api_base=settings.openai_base_url,
            model="text-embedding-3-small",
        )

    def _index_qdrant(self, session_id: str, texts: List[str]) -> int:
        embed_model = self._get_embed_model()
        Settings.embed_model = embed_model

        vector_store = QdrantVectorStore(
            client=self._qdrant,
            collection_name=f"session_{session_id}",
        )
        storage_context = StorageContext.from_defaults(vector_store=vector_store)

        documents = [Document(text=t) for t in texts]
        VectorStoreIndex.from_documents(documents, storage_context=storage_context)
        return len(documents)

    def _index_supabase(self, session_id: str, texts: List[str]) -> int:
        """Store chunks in Supabase for stateless cloud deployment."""
        db = get_supabase()
        chunks = []
        for t in texts:
            for i in range(0, len(t), 1000):
                chunk = t[i:i + 1000].strip()
                if chunk:
                    chunks.append(chunk)

        # Upsert chunks into a simple table (gracefully handle missing table)
        try:
            for idx, chunk in enumerate(chunks):
                db.table("document_chunks").upsert({
                    "session_id": session_id,
                    "chunk_index": idx,
                    "content": chunk,
                }).execute()
        except Exception as e:
            print(f"[VectorStore] Supabase chunks table missing ({e}), using in-memory only")

        # Always keep in-memory for fast follow-ups within the same instance
        self._fallback[session_id] = chunks
        return len(chunks)

    def query(self, session_id: str, query: str, top_k: int = 5) -> List[str]:
        if self._qdrant is not None:
            try:
                return self._query_qdrant(session_id, query, top_k)
            except Exception as e:
                print(f"[VectorStore] Qdrant query failed ({e}), falling back to Supabase")

        return self._query_supabase(session_id, query, top_k)

    def _query_supabase(self, session_id: str, query: str, top_k: int) -> List[str]:
        """Query Supabase chunks via simple keyword matching + in-memory cache."""
        # First check in-memory cache for this instance
        chunks = self._fallback.get(session_id, [])

        # If not in memory, try loading from Supabase
        if not chunks:
            try:
                db = get_supabase()
                resp = db.table("document_chunks").select("content").eq("session_id", session_id).execute()
                chunks = [r["content"] for r in resp.data]
                self._fallback[session_id] = chunks
            except Exception as e:
                # Table may not exist yet; just use in-memory
                print(f"[VectorStore] Supabase query failed ({e}), using in-memory only")

        if not chunks:
            return []

        query_words = set(query.lower().split())
        scored = []
        for c in chunks:
            score = sum(1 for w in query_words if w in c.lower())
            scored.append((score, c))
        scored.sort(key=lambda x: x[0], reverse=True)
        return [c for _, c in scored[:top_k]]

    def _query_qdrant(self, session_id: str, query: str, top_k: int) -> List[str]:
        embed_model = self._get_embed_model()
        Settings.embed_model = embed_model

        vector_store = QdrantVectorStore(
            client=self._qdrant,
            collection_name=f"session_{session_id}",
        )
        storage_context = StorageContext.from_defaults(vector_store=vector_store)
        index = VectorStoreIndex([], storage_context=storage_context)
        retriever = index.as_retriever(similarity_top_k=top_k)
        nodes = retriever.retrieve(query)
        return [n.text for n in nodes]

    def delete_session(self, session_id: str) -> None:
        if self._qdrant is not None:
            try:
                self._qdrant.delete_collection(f"session_{session_id}")
            except Exception:
                pass
        self._fallback.pop(session_id, None)
        try:
            db = get_supabase()
            db.table("document_chunks").delete().eq("session_id", session_id).execute()
        except Exception:
            pass
