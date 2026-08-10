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


def chunk_documents(documents, content_key="content", chunk_size=200, overlap=50):
    if chunk_size <= 0:
        raise ValueError("chunk_size must be a positive integer.")
    if overlap < 0:
        raise ValueError("overlap must be a non-negative integer.")
    if overlap >= chunk_size:
        raise ValueError("overlap must be less than chunk_size.")

    chunks = []
    for doc in documents:
        content = doc.get(content_key, "")
        
        stride = chunk_size - overlap
        start = 0
        idx = 0

        while start < len(content):
            end = min(start + chunk_size, len(content))

            chunk_dict = doc.copy()
            chunk_dict["chunk_id"] = idx
            chunk_dict["start"] = start
            chunk_dict[content_key] = content[start:end]

            chunks.append(chunk_dict)

            if end == len(content):
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
            CREATE TABLE IF NOT EXISTS documents (
                id TEXT NOT NULL,
                language TEXT,
                url TEXT,
                title TEXT,
                topic TEXT,
                chunk_id INT DEFAULT 0,
                start INT DEFAULT 0,
                content TEXT,
                embedding vector(768),
                source_urls TEXT[],
                PRIMARY KEY (id, language, chunk_id)
            );
        """)

        # create index for fast vector search using HNSW (Hierarchical Navigable Small World) algorithm
        conn.execute("""
            CREATE INDEX ON documents
            USING hnsw (embedding vector_cosine_ops)
        """)
        conn.commit()


def insert_documents(documents, embeddings):
    ensure_faq_table_exists()
    with get_db_connection() as conn:
        for doc, embedding in zip(documents, embeddings):
            conn.execute("""
                INSERT INTO documents
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                ON CONFLICT (id, language, chunk_id) DO NOTHING;
            """, (
                doc["id"],
                doc.get("language"),
                doc.get("url"),
                doc.get("title"),
                doc.get("topic"),
                doc.get("chunk_id", 0),
                doc.get("start"),
                doc.get("content"),
                embedding.tolist(),  # Convert numpy array to list for JSON serialization
                doc.get("source_urls"),
            ))
        conn.commit()