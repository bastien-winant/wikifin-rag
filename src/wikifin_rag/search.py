"""Hybrid and single-mode retrieval over the Wikifin document index."""

from typing import List
import json

from dotenv import load_dotenv
load_dotenv(override=True)

from pinecone import Pinecone, Document
from wikifin_rag.config import INDEX_NAME
from wikifin_rag.embedder import Embedder
from wikifin_rag.translate import to_dutch_query


_INCLUDE_FIELDS = ["title", "section", "text", "source_url"]

_pc = Pinecone(source_tag="pinecone:wikifin_search")
_embedder: Embedder | None = None


def _get_embedder() -> Embedder:
    """Lazy-load so the Streamlit UI can render before the ONNX model is ready."""
    global _embedder
    if _embedder is None:
        _embedder = Embedder()
    return _embedder


def _index():
    """Per-call index handle."""
    return _pc.index(name=INDEX_NAME)


def _execute(kwargs: dict) -> List[Document]:
    results = _index().documents.search(**kwargs)
    return list(map(lambda x: x.to_json(), results.matches))


# -----------------------------------------------------------------------------
# Search helpers
# -----------------------------------------------------------------------------

def text_search(query: str, field: str = "text", top_k: int = 10, language: str = "nl") -> List[str]:
    """Single-field FTS over one of title / description / section / text. BM25 token-OR.

    This is the most basic way to search Wikifin pages. Each word gains an "OR", so
    results will contain any of the query words. Notably, this does not preserve
    phrases or word order.

    Multi-word queries match documents that contain *any* of the words —
    documents matching more words score higher.
    """
    return _execute({
        "namespace": "__default__",
        "top_k": top_k,
        "score_by": [{"type": "text", "fields": [field], "query": query}],
        "include_fields": _INCLUDE_FIELDS,
        "filter": {"language": language},
    })


def vector_search(query: str, field: str = "embedding", top_k: int = 10, language: str = "nl") -> List[str]:
    query_embedding = _get_embedder().encode(query)

    return _execute({
        "namespace": "__default__",
        "top_k": top_k,
        "score_by": [{"type": "dense_vector", "field": field, "values": query_embedding}],
        "include_fields": _INCLUDE_FIELDS,
        "filter": {"language": language},
    })


def _reciprocal_rank_fusion(rankings, k=60):
    """Fuse ranked lists of document IDs into one RRF-scored ranking.

    Each ranking is a list of `_id`s in rank order (best first).
    Returns a dict mapping `_id` to its fused score.
    """
    scores = {}
    for ranking in rankings:
        for rank, doc_id in enumerate(ranking, start=1):
            scores[doc_id] = scores.get(doc_id, 0.0) + 1.0 / (k + rank)
    return scores


def rff_search(query: str, top_k: int = 10, language: str = "nl") -> List[str]:
    """Hybrid search: Dutch FTS + multilingual dense, fused with RRF.

    Non-Dutch queries are translated to Dutch for full-text search. Dense
    retrieval keeps the original query (multilingual embeddings). If
    translation fails, falls back to dense-only results.
    """
    dense_hits = vector_search(query=query, top_k=top_k, language=language)

    dutch_query = to_dutch_query(query)
    if dutch_query is None:
        return dense_hits[:top_k]

    text_hits = text_search(query=dutch_query, top_k=top_k, language=language)

    text_hits_ids = list(map(lambda x: json.loads(x).get("_id"), text_hits))
    dense_hits_ids = list(map(lambda x: json.loads(x).get("_id"), dense_hits))

    fused = _reciprocal_rank_fusion([text_hits_ids, dense_hits_ids])

    by_id = dict(zip(text_hits_ids, text_hits))
    for id, hit in zip(dense_hits_ids, dense_hits):
        by_id.setdefault(id, hit)

    return [by_id[doc_id] for doc_id in sorted(fused, key=fused.get, reverse=True)[:top_k]]
