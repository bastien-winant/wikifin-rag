from typing import Dict, List

from pinecone import Index

from wikifin_rag.crawler.crawler.items import Batch
from wikifin_rag.embedder import Embedder

_CHUNK_SIZE = 1200
_CHUNK_OVERLAP = 250


def _chunk_document(text: str, chunk_size: int, overlap: int) -> List[str]:
    if chunk_size <= 0:
        raise ValueError("chunk_size must be > 0")
    if not 0 <= overlap < chunk_size:
        raise ValueError("overlap must satisfy 0 <= overlap < chunk_size")

    length = len(text)
    step = chunk_size - overlap
    stop = max(length - overlap, 1)

    return [text[i:i + chunk_size] for i in range(0, stop, step)]


def _chunk_batch(
    docs: Batch,
    chunk_size: int = _CHUNK_SIZE,
    overlap: int = _CHUNK_OVERLAP,
) -> List[Dict]:
    return [
        {
            "id": f"{d.id}#{i}",
            "title": d.title,
            "description": d.description,
            "section": d.section,
            "text": part,
            "language": d.language,
            "source_url": d.source_url,
            "updated_on": d.updated_on
        }
        for d in docs
        for i, part in enumerate(_chunk_document(d.content, chunk_size=chunk_size, overlap=overlap))
    ]


def _encode_batch(chunks: List[Dict]) -> List[Dict]:
    embedder = Embedder()

    texts = [f"Document: {chunk['title']}\nSection: {chunk['section']}\n\n{chunk['text']}" for chunk in chunks]
    embeddings = embedder.encode_batch(texts)

    num_chunks = len(chunks)

    return [
        {
            "_id": chunks[i]["id"],
            "title": chunks[i]["title"],
            "description": chunks[i]["description"],
            "section": chunks[i]["section"],
            "text": chunks[i]["text"],
            "embedding": embeddings[i],
            "language": chunks[i]["language"],
            "source_url": chunks[i]["source_url"],
            "updated_on": chunks[i]["updated_on"]
        } for i in range(num_chunks)
    ]



def insert_batch(index: Index, batch: Batch) -> None:
    try:
        chunked_batch = _chunk_batch(batch)
        embeddings = _encode_batch(chunked_batch)

        index.documents.upsert(
            namespace="__default__",
            documents=embeddings
        )
    except Exception as e:
        print(f"DATA INSERTION ERROR: {e}")