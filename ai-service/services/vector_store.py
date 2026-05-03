"""
ChromaDB-backed vector store for compliance knowledge base.
Thread-safe singleton with lazy initialisation and seed data.
"""

import logging
import os
import threading
from typing import Dict, List

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Suppress ChromaDB telemetry (set BEFORE any chromadb import elsewhere)
# ---------------------------------------------------------------------------
os.environ["ANONYMIZED_TELEMETRY"] = "False"
os.environ["CHROMA_TELEMETRY"] = "False"

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------
COLLECTION_NAME = "ethics_knowledge"
EMBEDDING_MODEL_NAME = "all-MiniLM-L6-v2"
TOP_K = 3
MIN_RELEVANCE_SCORE = 0.4

# ---------------------------------------------------------------------------
# Thread-safe singletons
# ---------------------------------------------------------------------------
_lock = threading.RLock()
_model = None
_collection = None

# ---------------------------------------------------------------------------
# Seed documents
# ---------------------------------------------------------------------------
SEED_DOCUMENTS = [
    {
        "text": (
            "Financial fraud includes embezzlement, falsifying financial statements, "
            "insider trading, and misappropriation of funds. Under SOX (Sarbanes-Oxley Act) "
            "and the Dodd-Frank Act, companies must maintain internal controls and whistleblower "
            "protections. Suspected fraud should be reported immediately to the ethics hotline "
            "and the compliance officer for investigation."
        ),
        "source": "Financial Fraud & SOX/Dodd-Frank Policy",
    },
    {
        "text": (
            "Workplace harassment encompasses sexual harassment, bullying, intimidation, "
            "and hostile work environment behaviours. The organisation maintains a zero-tolerance "
            "policy. All complaints must be investigated within 14 days of receipt. Victims are "
            "entitled to interim protective measures during the investigation period."
        ),
        "source": "Workplace Harassment Zero-Tolerance Policy",
    },
    {
        "text": (
            "Safety violations include failure to follow OSHA regulations, operating equipment "
            "without proper training, ignoring safety protocols, and not reporting workplace "
            "injuries. Critical safety incidents must be reported within 24 hours to the safety "
            "officer and regulatory authorities as required by law."
        ),
        "source": "Safety Violations & OSHA Compliance",
    },
    {
        "text": (
            "Corruption and bribery involve offering, giving, receiving, or soliciting anything "
            "of value to influence business decisions. Employees must report suspected corruption "
            "through the ethics hotline. Each report is assigned a unique case number and "
            "investigated by the internal audit team within 30 days."
        ),
        "source": "Anti-Corruption & Bribery Policy",
    },
    {
        "text": (
            "Discrimination based on race, gender, age, religion, disability, sexual orientation, "
            "or any other protected characteristic is strictly prohibited. Complaints are handled "
            "confidentially, and the organisation provides reasonable accommodations as required "
            "by the ADA and equivalent regulations."
        ),
        "source": "Anti-Discrimination & Equal Opportunity Policy",
    },
    {
        "text": (
            "Retaliation against whistleblowers is strictly prohibited. Any employee who reports "
            "misconduct in good faith is protected from adverse employment actions, including "
            "termination, demotion, and harassment. Suspected retaliation must be reported within "
            "48 hours of occurrence and is escalated to the board-level ethics committee."
        ),
        "source": "Whistleblower Retaliation Protection Policy",
    },
    {
        "text": (
            "Internal investigation procedures require that all reported incidents be logged, "
            "assigned to a qualified investigator, and completed within 30 days. A summary report "
            "must be submitted to the board of directors. Evidence must be preserved, and "
            "confidentiality maintained throughout the process."
        ),
        "source": "Internal Investigation Procedures",
    },
    {
        "text": (
            "Data privacy violations include unauthorised access to personal data, failure to "
            "obtain consent, and data breaches. Under GDPR, organisations must notify affected "
            "individuals and supervisory authorities within 72 hours of becoming aware of a "
            "breach. All employees must complete annual data privacy training."
        ),
        "source": "Data Privacy & GDPR Compliance",
    },
    {
        "text": (
            "Conflicts of interest arise when an employee's personal interests interfere with "
            "their professional duties. All employees must submit an annual conflict-of-interest "
            "declaration. Undisclosed conflicts may result in disciplinary action, including "
            "termination and legal proceedings."
        ),
        "source": "Conflict of Interest Policy",
    },
    {
        "text": (
            "The ethics hotline handles all incoming reports through a structured triage process. "
            "Reports are classified by severity: Critical (immediate danger/large-scale fraud), "
            "High (serious policy violation), Medium (moderate concerns), Low (minor issues). "
            "Critical reports are escalated within 4 hours to the Chief Compliance Officer."
        ),
        "source": "Ethics Hotline Case Handling & Triage",
    },
]


def _get_model():
    """Return the singleton SentenceTransformer model (double-checked locking)."""
    global _model
    if _model is not None:
        return _model
    with _lock:
        if _model is not None:
            return _model
        from sentence_transformers import SentenceTransformer

        logger.info("Loading embedding model: %s", EMBEDDING_MODEL_NAME)
        _model = SentenceTransformer(EMBEDDING_MODEL_NAME)
        logger.info("Embedding model loaded.")
        return _model


def _get_collection():
    """Return the singleton ChromaDB collection (lazy, thread-safe)."""
    global _collection
    if _collection is not None:
        return _collection
    with _lock:
        if _collection is not None:
            return _collection
        import chromadb
        from chromadb.config import Settings

        persist_dir = os.getenv("CHROMA_PERSIST_DIR", "./chroma_data")
        logger.info("Initialising ChromaDB at: %s", persist_dir)

        client = chromadb.PersistentClient(
            path=persist_dir,
            settings=Settings(anonymized_telemetry=False),
        )
        _collection = client.get_or_create_collection(
            name=COLLECTION_NAME,
            metadata={"hnsw:space": "cosine"},
        )

        # Auto-seed if empty
        if _collection.count() == 0:
            logger.info("Seeding %d documents into %s …", len(SEED_DOCUMENTS), COLLECTION_NAME)
            _seed_collection(_collection)

        logger.info(
            "ChromaDB collection '%s' ready (%d documents).",
            COLLECTION_NAME,
            _collection.count(),
        )
        return _collection


def _seed_collection(collection) -> None:
    """Insert seed documents into an empty collection."""
    model = _get_model()
    texts = [doc["text"] for doc in SEED_DOCUMENTS]
    embeddings = model.encode(texts).tolist()

    collection.add(
        ids=[f"seed_{i}" for i in range(len(SEED_DOCUMENTS))],
        documents=texts,
        embeddings=embeddings,
        metadatas=[{"source": doc["source"]} for doc in SEED_DOCUMENTS],
    )
    logger.info("Seeded %d documents.", len(SEED_DOCUMENTS))


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def initialise() -> None:
    """Pre-load the model and collection (called at startup)."""
    _get_model()
    _get_collection()


def add_documents(docs: List[Dict]) -> int:
    """Add documents to the collection. Each dict must have 'text' and 'source'."""
    collection = _get_collection()
    model = _get_model()

    texts = [d["text"] for d in docs]
    embeddings = model.encode(texts).tolist()
    existing = collection.count()

    ids = [f"doc_{existing + i}" for i in range(len(docs))]
    metadatas = [{"source": d.get("source", "unknown")} for d in docs]

    with _lock:
        collection.add(
            ids=ids,
            documents=texts,
            embeddings=embeddings,
            metadatas=metadatas,
        )

    logger.info("Added %d documents (total now: %d).", len(docs), collection.count())
    return len(docs)


def similarity_search(query: str, top_k: int = TOP_K) -> List[Dict]:
    """Search for semantically similar documents.

    Returns list of dicts with keys: text, source, score.
    Filters results below ``MIN_RELEVANCE_SCORE``.
    """
    # Log query length NOT content (PII)
    logger.info("Similarity search (query_length=%d, top_k=%d)", len(query), top_k)

    collection = _get_collection()
    model = _get_model()

    embedding = model.encode([query]).tolist()

    # Fetch more candidates to improve filtering
    fetch_k = top_k * 2
    results = collection.query(
        query_embeddings=embedding,
        n_results=fetch_k,
        include=["documents", "metadatas", "distances"],
    )

    documents = results.get("documents", [[]])[0]
    metadatas = results.get("metadatas", [[]])[0]
    distances = results.get("distances", [[]])[0]

    filtered: List[Dict] = []
    for doc, meta, dist in zip(documents, metadatas, distances):
        score = 1.0 - (dist / 2.0)
        if score >= MIN_RELEVANCE_SCORE:
            filtered.append(
                {
                    "text": doc,
                    "source": meta.get("source", "unknown"),
                    "score": round(score, 4),
                }
            )
        if len(filtered) >= top_k:
            break

    logger.info("Search returned %d results (filtered from %d).", len(filtered), len(documents))
    return filtered


def document_count() -> int:
    """Return the total number of documents in the collection."""
    return _get_collection().count()
