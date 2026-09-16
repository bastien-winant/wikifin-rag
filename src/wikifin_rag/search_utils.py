from sqlitesearch import TextSearchIndex, VectorSearchIndex
from wikifin_rag.config import PROJECT_ROOT


def compute_rrf(rank, k=60):
    return 1 / (k + rank)


def rrf_hybrid_search(search_results, num_results=5, k=60):
    scores = {}
    doc_map = {}

    for results in search_results:
        for rank, doc in enumerate(results):
            key = doc["id"]
            doc_map[key] = doc
            scores[key] = scores.get(key, 0) + compute_rrf(rank, k)

    ranked = sorted(scores.items(), key=lambda x: x[1], reverse=True)
    return [doc_map[key] for key, _ in ranked[:num_results]]


def build_text_index(documents, db_path=PROJECT_ROOT / "db" / "sqlitesearch_text.db", **params):
    index = TextSearchIndex(
        text_fields=['title', 'section', 'content'],
        db_path=db_path,
        **params
    )

    index.clear()
    return index.fit(documents)


def build_vector_index(vectors, documents, db_path=PROJECT_ROOT / "db" / "sqlitesearch_vectors.db", **params):
    index = VectorSearchIndex(
        db_path=db_path,
        **params
    )
    
    index.clear()
    return index.fit(vectors, documents)


def load_text_index(db_path=PROJECT_ROOT / "db" / "sqlitesearch_text.db", **params):
    index = TextSearchIndex(
        db_path=db_path,
        text_fields=['title', 'section', 'content'],
        **params
    )

    return index


def load_vector_index(db_path=PROJECT_ROOT / "db" / "sqlitesearch_vectors.db", **params):
    index = VectorSearchIndex(
        db_path=db_path,
        **params
    )

    return index


def text_search(query, index, num_results=5, boost_dict=None):
    return index.search(
        query,
        num_results=num_results,
        boost_dict=boost_dict
    )


def vector_search(query, index, embedder, num_results=5):
    query_vector = embedder.encode(query)
    return index.search(
        query_vector,
        num_results=num_results
    )