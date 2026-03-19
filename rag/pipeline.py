"""
FinSentinel AI - RAG Pipeline
Production-grade Retrieval-Augmented Generation for financial documents.
Supports: ChromaDB (local), Qdrant, Azure Cognitive Search
"""
from __future__ import annotations
import logging
from pathlib import Path
from typing import Any, Optional

from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain_community.document_loaders import (
    PyPDFLoader, TextLoader, JSONLoader, CSVLoader
)
from langchain_core.documents import Document

from config.settings import get_settings
from llm.providers.factory import get_llm_provider

logger = logging.getLogger(__name__)


class FinancialRAGPipeline:
    """
    RAG pipeline tuned for financial documents:
    - Chunk overlap preserved for regulatory context
    - Metadata-rich indexing (source, date, department, classification)
    - Hybrid search (semantic + keyword) for compliance accuracy
    """

    CHUNK_SIZE = 512
    CHUNK_OVERLAP = 100

    def __init__(self):
        self.settings = get_settings()
        self.provider = get_llm_provider(self.settings)
        self.embedder = self.provider.get_embedding_model()
        self.vector_store = self._init_vector_store()
        self.text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=self.CHUNK_SIZE,
            chunk_overlap=self.CHUNK_OVERLAP,
            separators=["\n\n", "\n", ".", " "],
        )

    def _init_vector_store(self):
        backend = self.settings.VECTOR_STORE
        if backend == "chroma":
            from langchain_chroma import Chroma
            return Chroma(
                collection_name="finsentinel_kb",
                embedding_function=self.embedder,
                persist_directory="./data/chroma_db",
            )
        elif backend == "qdrant":
            from langchain_qdrant import Qdrant
            from qdrant_client import QdrantClient
            client = QdrantClient(
                host=self.settings.QDRANT_HOST,
                port=self.settings.QDRANT_PORT,
            )
            return Qdrant(
                client=client,
                collection_name="finsentinel_kb",
                embeddings=self.embedder,
            )
        elif backend == "azure_cognitive_search":
            from langchain_community.vectorstores import AzureSearch
            return AzureSearch(
                azure_search_endpoint=self.settings.AZURE_SEARCH_ENDPOINT,
                azure_search_key=self.settings.AZURE_SEARCH_KEY,
                index_name=self.settings.AZURE_SEARCH_INDEX,
                embedding_function=self.embedder.embed_query,
            )
        else:
            raise ValueError(f"Unsupported vector store: {backend}")

    def load_document(self, file_path: str, metadata: Optional[dict] = None) -> list[Document]:
        """Load and chunk a financial document."""
        path = Path(file_path)
        ext = path.suffix.lower()

        loaders = {
            ".pdf": lambda: PyPDFLoader(file_path),
            ".txt": lambda: TextLoader(file_path),
            ".csv": lambda: CSVLoader(file_path),
            ".json": lambda: JSONLoader(file_path, jq_schema=".", text_content=False),
        }

        loader_fn = loaders.get(ext)
        if not loader_fn:
            raise ValueError(f"Unsupported file type: {ext}")

        docs = loader_fn().load()
        chunks = self.text_splitter.split_documents(docs)

        if metadata:
            for chunk in chunks:
                chunk.metadata.update(metadata)

        logger.info(f"Loaded {path.name}: {len(docs)} pages → {len(chunks)} chunks")
        return chunks

    async def ingest(self, file_path: str, metadata: Optional[dict] = None) -> dict:
        """Ingest a document into the vector store."""
        chunks = self.load_document(file_path, metadata)
        self.vector_store.add_documents(chunks)
        return {
            "file": file_path,
            "chunks_ingested": len(chunks),
            "vector_store": self.settings.VECTOR_STORE,
        }

    async def retrieve(
        self,
        query: str,
        top_k: int = 5,
        filters: Optional[dict] = None,
    ) -> list[dict]:
        """Semantic retrieval from the knowledge base."""
        retriever_kwargs = {"k": top_k}
        if filters:
            retriever_kwargs["filter"] = filters

        docs = self.vector_store.similarity_search_with_score(query, **retriever_kwargs)

        return [
            {
                "content": doc.page_content,
                "metadata": doc.metadata,
                "score": float(score),
                "source": doc.metadata.get("source", "unknown"),
            }
            for doc, score in docs
        ]

    async def answer_with_context(self, query: str, top_k: int = 5) -> dict:
        """Full RAG: retrieve context + generate grounded answer."""
        context_docs = await self.retrieve(query, top_k)
        context = "\n\n---\n\n".join([d["content"] for d in context_docs])

        llm = self.provider.get_chat_model()
        from langchain_core.messages import HumanMessage, SystemMessage

        response = await llm.ainvoke([
            SystemMessage(content=(
                "You are a financial expert. Answer using ONLY the provided context. "
                "If the context doesn't contain the answer, say so explicitly. "
                "Always cite the source document."
            )),
            HumanMessage(content=f"Context:\n{context}\n\nQuestion: {query}"),
        ])

        return {
            "answer": response.content,
            "sources": [d["source"] for d in context_docs],
            "context_chunks": len(context_docs),
        }
