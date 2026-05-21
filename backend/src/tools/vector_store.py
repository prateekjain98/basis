"""Qdrant vector store — one collection per session."""

from __future__ import annotations

from typing import List

from llama_index.core import Document, StorageContext, VectorStoreIndex
from llama_index.core.node_parser import SentenceSplitter
from llama_index.vector_stores.qdrant import QdrantVectorStore
from qdrant_client import QdrantClient

from src.config import settings


class SessionVectorStore:
    def __init__(self) -> None:
        self.client = QdrantClient(url=settings.qdrant_url)

    def index_documents(self, session_id: str, texts: List[str]) -> int:
        collection = f"session_{session_id}"
        self.client.delete_collection(collection)

        store = QdrantVectorStore(
            client=self.client,
            collection_name=collection,
            dimension=1536,
        )
        ctx = StorageContext.from_defaults(vector_store=store)
        docs = [Document(text=t) for t in texts if t.strip()]
        if not docs:
            return 0

        nodes = SentenceSplitter(chunk_size=512, chunk_overlap=64).get_nodes_from_documents(docs)
        VectorStoreIndex(nodes, storage_context=ctx)
        return len(nodes)

    def query(self, session_id: str, query: str, top_k: int = 5) -> List[str]:
        collection = f"session_{session_id}"
        if not self.client.collection_exists(collection):
            return []

        store = QdrantVectorStore(client=self.client, collection_name=collection)
        index = VectorStoreIndex.from_vector_store(store)
        return [n.text for n in index.as_retriever(similarity_top_k=top_k).retrieve(query)]

    def delete_session(self, session_id: str) -> None:
        collection = f"session_{session_id}"
        if self.client.collection_exists(collection):
            self.client.delete_collection(collection)
