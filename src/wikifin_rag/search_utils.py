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