"""
services/vector_store.py
=========================
Manages the ChromaDB vector store and ChromaDB embedding function.

Responsibilities:
  - Create / reuse the 'complaints' ChromaDB collection
  - Use ChromaDB's DefaultEmbeddingFunction for text embedding
  - Seed domain knowledge documents on first run
  - Expose: add_documents(), similarity_search(), query_knowledge(),
            document_count(), is_chromadb_connected()

Thread safety: _get_collection() uses double-checked locking via a threading.RLock
so the collection is initialised only once in concurrent requests.
"""

import os
import logging
import hashlib
import threading
from typing import List, Dict, Any
from dotenv import load_dotenv
load_dotenv()
import chromadb
from chromadb.utils import embedding_functions

logger = logging.getLogger(__name__)

# ── Configuration ─────────────────────────────────────────────────────────────
COLLECTION_NAME = "complaints"
TOP_K = 3          # default number of results returned by similarity_search
MIN_RELEVANCE_SCORE = 0.4  # filter out low-relevance results

# Export the model name so /health can import it instead of hardcoding a magic
# string that may drift out of sync.
EMBEDDING_MODEL_NAME = "all-MiniLM-L6-v2"

# ── Domain knowledge seed documents ──────────────────────────────────────────
_SEED_DOCUMENTS: List[Dict[str, str]] = [
    {
        "id": "doc_fraud_001",
        "text": (
            "Financial fraud in organisations includes misrepresentation of accounts, "
            "embezzlement of company funds, falsification of financial statements, and "
            "bribery of officials. Whistleblowers who report financial fraud are protected "
            "under legislation such as the Sarbanes-Oxley Act and the Dodd-Frank Act. "
            "Investigators should secure all financial records and restrict access immediately."
        ),
        "source": "Compliance Handbook — Financial Fraud",
    },
    {
        "id": "doc_harassment_001",
        "text": (
            "Workplace harassment encompasses verbal abuse, bullying, sexual harassment, "
            "and creating a hostile work environment. Organisations must have a zero-tolerance "
            "policy. All reports must be treated confidentially, investigated within 14 days, "
            "and the complainant must not suffer retaliation. HR and Legal must be notified "
            "immediately upon receiving a harassment complaint."
        ),
        "source": "HR Policy — Harassment and Bullying",
    },
    {
        "id": "doc_safety_001",
        "text": (
            "Workplace safety violations include ignoring OSHA regulations, failure to provide "
            "personal protective equipment, unsafe machinery operation, and improper handling of "
            "hazardous materials. Safety incidents must be reported to the Health & Safety officer "
            "within 24 hours. Root cause analysis must be completed within 7 days of the incident. "
            "Repeat violations may result in regulatory fines and facility shutdown."
        ),
        "source": "Health & Safety Manual — Incident Reporting",
    },
    {
        "id": "doc_corruption_001",
        "text": (
            "Corruption includes accepting or offering bribes, conflicts of interest, nepotism, "
            "and misuse of authority for personal gain. Public officials and corporate executives "
            "found guilty of corruption face criminal prosecution, fines, and disqualification. "
            "Ethics hotlines are the primary channel for reporting suspected corruption anonymously. "
            "All reports are logged, assigned a case number, and reviewed by the ethics committee."
        ),
        "source": "Anti-Corruption Policy — Ethics Committee",
    },
    {
        "id": "doc_discrimination_001",
        "text": (
            "Discrimination on the basis of race, gender, age, religion, disability, or sexual "
            "orientation is illegal in most jurisdictions and violates corporate policy. "
            "Reports of discrimination must be investigated impartially by HR and Legal. "
            "Evidence including emails, meeting notes, and witness statements should be preserved. "
            "Corrective actions range from mandatory training to termination."
        ),
        "source": "Equal Opportunity Policy — Anti-Discrimination",
    },
    {
        "id": "doc_retaliation_001",
        "text": (
            "Retaliation against whistleblowers is illegal and constitutes a separate violation. "
            "Forms of retaliation include demotion, pay cuts, exclusion from meetings, negative "
            "performance reviews, or termination. Any person who reports retaliation will receive "
            "immediate protection. The ethics committee must be notified within 48 hours of a "
            "retaliation allegation, and an independent review must be initiated."
        ),
        "source": "Whistleblower Protection Policy",
    },
    {
        "id": "doc_investigation_001",
        "text": (
            "Internal investigations must be conducted by qualified personnel who have no conflict "
            "of interest with the parties involved. The investigation must be documented with a "
            "formal case file, interview records, evidence logs, and a final report. Findings must "
            "be reported to the board or audit committee within 30 days. External legal counsel "
            "may be engaged for high-severity cases involving potential criminal conduct."
        ),
        "source": "Investigation Procedures — Internal Audit",
    },
    {
        "id": "doc_data_privacy_001",
        "text": (
            "Data privacy violations include unauthorised access to personal data, sharing customer "
            "information without consent, and failure to comply with GDPR or CCPA. "
            "A data breach must be reported to the relevant regulatory authority within 72 hours. "
            "Affected individuals must be notified promptly. The DPO (Data Protection Officer) "
            "leads the response and coordinates with Legal and IT Security."
        ),
        "source": "Data Privacy Policy — GDPR Compliance",
    },
    {
        "id": "doc_conflict_of_interest_001",
        "text": (
            "A conflict of interest arises when an employee's personal interests interfere with "
            "their professional responsibilities. Examples include awarding contracts to family "
            "members, holding financial interests in a competitor, or receiving gifts from vendors. "
            "Employees must declare conflicts of interest annually and immediately upon discovery. "
            "Undisclosed conflicts are treated as a disciplinary offence."
        ),
        "source": "Conflict of Interest Policy",
    },
    {
        "id": "doc_reporting_procedure_001",
        "text": (
            "Reports submitted via the ethics hotline are assigned a unique case number within "
            "one business day. The case is triaged by severity: Critical cases are escalated "
            "to the board within 24 hours; High severity within 72 hours; Medium within 7 days; "
            "Low within 30 days. All reporters may submit anonymous follow-ups using their case "
            "number. Reporters are updated on case status at each major milestone."
        ),
        "source": "Ethics Hotline — Case Handling Procedure",
    },
]

# ── Singleton state ───────────────────────────────────────────────────────────
_init_lock = threading.RLock()
_client = None
_collection = None
_initialised = False


def _get_collection() -> chromadb.Collection:
    """
    Return the ChromaDB collection, creating client + collection if needed.
    Seeds domain documents on first creation. Thread-safe via double-checked locking.
    """
    global _client, _collection, _initialised

    if _initialised:
        return _collection

    with _init_lock:
        if _initialised:
            return _collection

        persist_dir = os.getenv("CHROMA_PERSIST_DIR")
        if persist_dir:
            os.makedirs(persist_dir, exist_ok=True)
            _client = chromadb.PersistentClient(path=persist_dir)
            logger.info("ChromaDB using persistent storage at %s", persist_dir)
        else:
            # FIX: chromadb.Client() is deprecated and removed in modern chromadb.
            # Use EphemeralClient() for in-memory storage.
            _client = chromadb.EphemeralClient()
            logger.info("ChromaDB using in-memory storage (no CHROMA_PERSIST_DIR set)")

        ef = embedding_functions.DefaultEmbeddingFunction()

        # FIX: Explicitly set hnsw:space to "cosine" so that ChromaDB returns
        # cosine distances (range 0–2). Without this, ChromaDB defaults to L2
        # (Euclidean) distances which are unbounded, making the
        # `1.0 - (distance / 2.0)` similarity formula produce wrong/negative scores.
        _collection = _client.get_or_create_collection(
            name=COLLECTION_NAME,
            embedding_function=ef,
            metadata={"hnsw:space": "cosine"},
        )
        logger.info(
            "Collection '%s' ready (cosine metric). Documents stored: %d",
            COLLECTION_NAME,
            _collection.count(),
        )

        if _collection.count() == 0:
            logger.info("Seeding %d domain knowledge documents …", len(_SEED_DOCUMENTS))
            _seed_documents(_collection)
            logger.info("Seeding complete. Total documents: %d", _collection.count())

        _initialised = True

    return _collection


def _seed_documents(coll: chromadb.Collection) -> None:
    """Insert the built-in seed documents into the given collection."""
    ids = [doc["id"] for doc in _SEED_DOCUMENTS]
    texts = [doc["text"] for doc in _SEED_DOCUMENTS]
    metadatas = [{"source": doc["source"]} for doc in _SEED_DOCUMENTS]

    coll.add(
        ids=ids,
        documents=texts,
        metadatas=metadatas,
    )


# ── Public API ────────────────────────────────────────────────────────────────

def initialise() -> None:
    """
    Pre-load collection at app startup.
    Call this from app.py so the first /query request is not slow.
    """
    _get_collection()
    logger.info("VectorStore initialised and ready.")


def add_documents(documents: List[Dict[str, str]]) -> int:
    """
    Add documents to the vector store.

    Each dict must have:
      - "text"   : the document content (required)
      - "source" : human-readable source label (optional, defaults to "custom")
      - "id"     : stable unique id (optional — SHA256 of text used if omitted)

    Returns the number of documents successfully added.
    """
    if not documents:
        return 0

    coll = _get_collection()

    ids, texts, metadatas = [], [], []
    for doc in documents:
        text = doc.get("text", "").strip()
        if not text:
            continue
        doc_id = doc.get("id") or hashlib.sha256(text.encode()).hexdigest()[:16]
        source = doc.get("source", "custom")
        ids.append(doc_id)
        texts.append(text)
        metadatas.append({"source": source})

    if not ids:
        return 0

    # Use upsert() so re-adding a document with the same ID updates it instead
    # of crashing with a duplicate ID error.
    coll.upsert(
        ids=ids,
        documents=texts,
        metadatas=metadatas,
    )
    logger.info("Upserted %d document(s) into ChromaDB.", len(ids))
    return len(ids)


def similarity_search(query: str, top_k: int = TOP_K) -> List[Dict[str, Any]]:
    """
    Embed the query and return the top_k most similar documents above the
    minimum relevance threshold (MIN_RELEVANCE_SCORE).

    Returns a list of dicts:
      [
        {
          "text": "...",
          "source": "...",
          "score": 0.92          # cosine similarity (0–1, higher = more similar)
        },
        ...
      ]
    Returns an empty list if the collection is empty or an error occurs.
    """
    try:
        coll = _get_collection()
        if coll.count() == 0:
            logger.warning("similarity_search called on empty collection.")
            return []

        results = coll.query(
            query_texts=[query],
            # Fetch twice as many candidates before filtering so that if fewer
            # than top_k pass the relevance threshold we still surface the best
            # available results rather than returning an empty list.
            n_results=min(top_k * 2, coll.count()),
            include=["documents", "metadatas", "distances"],
        )

        output: List[Dict[str, Any]] = []
        docs = results.get("documents", [[]])[0]
        metas = results.get("metadatas", [[]])[0]
        distances = results.get("distances", [[]])[0]

        for doc_text, meta, distance in zip(docs, metas, distances):
            # Cosine distance returned by ChromaDB: 0 = identical, 2 = opposite.
            # The collection is created with hnsw:space=cosine (see _get_collection),
            # so this formula is always correct.
            similarity = round(1.0 - (distance / 2.0), 4)
            if similarity >= MIN_RELEVANCE_SCORE:
                output.append({
                    "text": doc_text,
                    "source": meta.get("source", "unknown"),
                    "score": similarity,
                })
                if len(output) == top_k:
                    break

        logger.info(
            "similarity_search returned %d results for query (first 60 chars): '%s…'",
            len(output),
            query[:60],
        )
        return output

    except Exception as exc:
        logger.error("similarity_search failed: %s", exc)
        return []


def query_knowledge(text: str, n_results: int = TOP_K) -> List[str]:
    """
    Return the top-n_results relevant document texts for *text*, respecting
    MIN_RELEVANCE_SCORE so low-quality matches are excluded consistently with
    similarity_search.
    """
    try:
        coll = _get_collection()
        if coll.count() == 0:
            return []

        # FIX: Reuse similarity_search so MIN_RELEVANCE_SCORE filtering is applied
        # consistently. The previous direct coll.query() call bypassed the threshold,
        # allowing low-relevance noise to reach callers.
        results = similarity_search(text, top_k=n_results)
        return [r["text"] for r in results]

    except Exception as exc:
        logger.error("query_knowledge failed: %s", exc)
        return []


def is_chromadb_connected() -> bool:
    """Return ``True`` if the ChromaDB collection is reachable."""
    try:
        _get_collection().count()
        return True
    except Exception:
        return False


def document_count() -> int:
    """
    Return the total number of documents in the collection.
    Lets exceptions propagate so callers (e.g. /health) can distinguish
    "0 documents" from "ChromaDB is down" and report -1.
    """
    return _get_collection().count()