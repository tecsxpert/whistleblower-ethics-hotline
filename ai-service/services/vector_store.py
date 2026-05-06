"""
ChromaDB vector store — persistent collection seeded with
whistleblower-domain knowledge for RAG retrieval.
"""

import logging
import threading
from typing import List

import chromadb
from chromadb.utils import embedding_functions

logger = logging.getLogger(__name__)

# ── Singleton plumbing ───────────────────────────────────────────────
_lock = threading.Lock()
_collection = None
_chroma_client = None

COLLECTION_NAME = "whistleblower_knowledge"
PERSIST_DIR = "./chroma_data"
EMBED_MODEL = "all-MiniLM-L6-v2"

# ── Seed documents ───────────────────────────────────────────────────
_SEED_DOCUMENTS: list[str] = [
    "Whistleblower protection laws prohibit retaliation against employees who report misconduct in good faith.",
    "Ethics hotlines must maintain anonymity and confidentiality for all reporters to encourage participation.",
    "Financial fraud includes falsifying records, embezzlement, and misappropriation of company assets.",
    "Workplace harassment complaints should be investigated within 30 days by an impartial committee.",
    "Bribery and corruption reports require immediate escalation to senior management and legal counsel.",
    "Data privacy violations involving customer PII must be reported under GDPR within 72 hours.",
    "Conflict of interest must be disclosed when an employee has personal financial ties to a vendor or client.",
    "Safety violations in the workplace must be documented and corrected before resuming operations.",
    "Retaliation against a whistleblower is a serious legal offence that can result in criminal prosecution.",
    "Anonymous reports are treated with equal weight as identified reports during the investigation process.",
]


def _get_collection():
    """Return the ChromaDB collection (singleton, thread-safe)."""
    global _collection, _chroma_client
    if _collection is not None:
        return _collection

    with _lock:
        if _collection is not None:
            return _collection  # double-checked locking

        try:
            ef = embedding_functions.SentenceTransformerEmbeddingFunction(
                model_name=EMBED_MODEL
            )
            _chroma_client = chromadb.PersistentClient(path=PERSIST_DIR)
            _collection = _chroma_client.get_or_create_collection(
                name=COLLECTION_NAME,
                embedding_function=ef,
            )
            logger.info(
                "ChromaDB collection '%s' ready (%d docs).",
                COLLECTION_NAME,
                _collection.count(),
            )
        except Exception as exc:
            logger.error("Failed to initialise ChromaDB: %s", exc)
            _collection = None

    return _collection


def init_vector_store() -> None:
    """
    Initialise the vector store and seed the knowledge base.
    This MUST be called explicitly — NOT at module import time —
    so that tests can import this module without downloading ML models.
    """
    seed_knowledge_base()


def seed_knowledge_base() -> None:
    """Seed the collection with domain documents if it is empty."""
    try:
        collection = _get_collection()
        if collection is None:
            logger.warning("Cannot seed — ChromaDB collection unavailable.")
            return

        if collection.count() > 0:
            logger.info("Knowledge base already seeded (%d docs).", collection.count())
            return

        ids = [f"doc_{i}" for i in range(len(_SEED_DOCUMENTS))]
        collection.add(documents=_SEED_DOCUMENTS, ids=ids)
        logger.info("Seeded %d documents into '%s'.", len(_SEED_DOCUMENTS), COLLECTION_NAME)
    except Exception as exc:
        logger.error("Error seeding knowledge base: %s", exc)


def query_knowledge(text: str, n_results: int = 3) -> List[str]:
    """Return the top-*n_results* relevant documents for *text*."""
    try:
        collection = _get_collection()
        if collection is None or collection.count() == 0:
            return []
        results = collection.query(query_texts=[text], n_results=n_results)
        documents = results.get("documents", [[]])[0]
        return documents
    except Exception as exc:
        logger.error("query_knowledge failed: %s", exc)
        return []


def is_chromadb_connected() -> bool:
    """Return ``True`` if the ChromaDB collection is reachable."""
    try:
        collection = _get_collection()
        if collection is None:
            return False
        collection.count()
        return True
    except Exception:
        return False
