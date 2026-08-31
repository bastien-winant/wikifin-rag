def vec_to_str(vector):
    return f"[{",".join(str(x) for x in vector)}]"


def text_to_chunks(text, chunk_size, overlap):
    if chunk_size <= 0:
        raise ValueError("chunk_size must be > 0")
    if not 0 <= overlap < chunk_size:
        raise ValueError("overlap must satisfy 0 <= overlap < chunk_size")

    length = len(text)
    step = chunk_size - overlap

    chunks = {}

    for i in range(0, length - overlap, step):
        chunk = text[i:i + chunk_size]
        chunks[i] = chunk

    return chunks


def chunk_document_batch(batch, chunk_size, overlap):
    chunked_batch = []

    for document in batch:
        # split the document content into chunks
        chunks = text_to_chunks(document.content, chunk_size, overlap)

        for chunk_id, chunk_text in chunks.items():
            chunked_batch.append({
                "document_id": document.id, # keep the document ID for reference
                "chunk_id": chunk_id, # chunk sequence ID
                "title": document.title,
                "section": document.section,
                "content": chunk_text
            })

    return chunked_batch


def rrf(search_results, k=1, num_results=10):
    scores = {}
    doc_map = {}

    for results in search_results:
        for rank, doc in enumerate(results):
            key = doc["id"]
            if key not in scores:
                scores[key] = 0
                doc_map[key] = doc
            scores[key] += 1 / (k + rank + 1)

    ranked = sorted(scores.items(), key=lambda x: x[1], reverse=True)
    return [doc_map[key] for key, _ in ranked[:num_results]]