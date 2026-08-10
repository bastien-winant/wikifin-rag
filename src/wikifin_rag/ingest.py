import json
import os
import time
from dotenv import load_dotenv
from tqdm.auto import tqdm
import numpy as np
from embedder import Embedder
import psycopg


load_dotenv(override=True)


def load_corpus(filepath):
    with filepath.open("r", encoding="utf-8") as f:
        return [json.loads(line.strip()) for line in f if line.strip()]


def chunk_faq_data(documents, chunk_size=200, overlap=50):
    if chunk_size <= 0:
        raise ValueError("chunk_size must be a positive integer.")
    if overlap < 0:
        raise ValueError("overlap must be a non-negative integer.")
    if overlap >= chunk_size:
        raise ValueError("overlap must be less than chunk_size.")

    chunks = []
    for doc in documents:
        id = doc["id"]
        question = doc["question"]
        answer = doc["answer"]
        text = f"Question: {question}\nAnswer: {answer}"
        language = doc.get("language")
        page_url = doc.get("page_url")
        page_title = doc.get("page_title")
        source_urls = doc.get("source_urls", [])

        stride = chunk_size - overlap
        start = 0
        idx = 0

        while start < len(text):
            end = min(start + chunk_size, len(text))
            chunk_text = text[start:end]
            chunk_id = f"{id}_chunk_{idx}"
            chunks.append({
                "id": chunk_id,
                "content": chunk_text,
                "language": language,
                "page_url": page_url,
                "page_title": page_title,
                "source_urls": source_urls,
                "start": start
            })

            if end == len(text):
                break

            idx += 1
            start += stride
    return chunks


def embed_texts(texts, batch_size=50):
    embed = Embedder()

    X = []

    for i in tqdm(range(0, len(texts), batch_size)):
        batch = texts[i:i + batch_size]
        batch_vectors = embed.encode_batch(batch)
        X.extend(batch_vectors)

    return X


def get_db_connection():
    db_host = "localhost"
    db_port = 5432
    db_name = os.environ.get("POSTGRES_DB", "wikifin_rag")
    db_user = os.environ.get("POSTGRES_USER", "wikifin_rag_user")
    db_password = os.environ.get("POSTGRES_PASSWORD", "wikifin_rag_password")

    conn_str = f"host={db_host} port={db_port} dbname={db_name} user={db_user} password={db_password}"
    last_conn = None

    for attempt in range(5):
        try:
            return psycopg.connect(conn_str)
        except Exception as e:
            last_conn = e
            print(f"Attempt {attempt + 1} failed: {e}")
            if attempt < 4:
                time.sleep(2)
    raise last_conn
    

def ensure_faq_table_exists():
    with get_db_connection() as conn:
        conn.execute("CREATE EXTENSION IF NOT EXISTS vector;")
        conn.execute("""
            CREATE TABLE IF NOT EXISTS faq_chunks (
                id TEXT NOT NULL,
                language TEXT,
                page_url TEXT,
                page_title TEXT,
                source_urls TEXT[],
                start INT NOT NULL,
                content TEXT NOT NULL,
                embedding vector(768),
                PRIMARY KEY (id, start, language)
            );
        """)

        # create index for fast vector search using HNSW (Hierarchical Navigable Small World) algorithm
        conn.execute("""
            CREATE INDEX ON faq_chunks
            USING hnsw (embedding vector_cosine_ops)
        """)
        conn.commit()


def insert_faq_chunks(chunks, embeddings):
    with get_db_connection() as conn:
        for chunk, embedding in zip(chunks, embeddings):
            conn.execute("""
                INSERT INTO faq_chunks
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                ON CONFLICT (id, start, language) DO NOTHING;
            """, (
                chunk["id"],
                chunk.get("language"),
                chunk.get("page_url"),
                chunk.get("page_title"),
                chunk.get("source_urls"),
                chunk["start"],
                chunk["content"],
                embedding.tolist()  # Convert numpy array to list for JSON serialization
            ))
        conn.commit()