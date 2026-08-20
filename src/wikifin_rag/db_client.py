from dotenv import load_dotenv
import os
from psycopg import connect, sql, rows
from dataclasses import asdict
from wikifin_rag.embedder import Embedder
from wikifin_rag.config import PROJECT_ROOT
from wikifin_rag.utils import vec_to_str, text_to_chunks
import logging


class PostgresClient():
    def __init__(self, embedder=Embedder()):
        load_dotenv(override=True)

        self.documents_table_identifier = sql.Identifier("documents")
        self.chunks_table_identifier = sql.Identifier("chunks")

        self.db_host = "localhost"
        self.db_port = 5432
        self.db_name = os.environ['POSTGRES_DB']
        self.db_user = os.environ['POSTGRES_USER']
        self.db_password = os.environ['POSTGRES_PASSWORD']

        self.embedder = embedder

        self.logger = logging.getLogger(__name__)


    def open_connection(self, autocommit=True):
        try:
            self.con = connect(
                host=self.db_host,
                port=self.db_port,
                dbname=self.db_name,
                user=self.db_user,
                password=self.db_password,
                autocommit=autocommit,
                row_factory=rows.dict_row
            )

            self.cur = self.con.cursor()
        except Exception as e:
            self.logger.error(f"Unable to open the database connection: {e}")


    def close_connection(self):
        try:
            self.cur.close()
            self.con.close()
        except Exception as e:
            self.logger.error(f"Unable to close the database connection: {e}")


    def create_tables(self, drop=False):
        try:
            if drop:
                self.cur.execute(
                    sql.SQL("DROP TABLE IF EXISTS {};").format(self.chunks_table_identifier)
                )
                self.cur.execute(
                    sql.SQL("DROP TABLE IF EXISTS {};").format(self.documents_table_identifier)
                )

            self.cur.execute("CREATE EXTENSION IF NOT EXISTS vector;")

            self.cur.execute(
                sql.SQL(
                    """
                    CREATE TABLE IF NOT EXISTS {} (
                        id TEXT PRIMARY KEY,
                        source_url TEXT NOT NULL,
                        language TEXT,
                        updated_on DATE,
                        title TEXT,
                        description TEXT,
                        section TEXT,
                        html TEXT,
                        content TEXT,
                        related_links TEXT[],
                        updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
                    );
                    """
                ).format(self.documents_table_identifier)
            )
            
            self.cur.execute(
                sql.SQL(
                    """
                    CREATE TABLE IF NOT EXISTS {} (
                        document_id TEXT REFERENCES {} (id),
                        chunk_id TEXT NOT NULL,
                        content TEXT,
                        embedding vector(768),
                        updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
                        PRIMARY KEY (document_id, chunk_id)
                    );
                    """
                ).format(self.chunks_table_identifier, self.documents_table_identifier)
            )

            self.cur.execute(
                sql.SQL(
                    """
                    CREATE INDEX ON {}
                    USING hnsw (embedding vector_cosine_ops)
                    """
                ).format(self.chunks_table_identifier)
            )

            self.logger.info("The database tables have been created.")

        except Exception as e:
            self.logger.error(f"The tables could not be created: {e}")


    def chunk_batch(self, batch, chunk_size, overlap):
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



    def insert_batch(self, batch):
        try:
            # UPLOAD DOCUMENTS
            self.cur.executemany(
                sql.SQL(
                    """
                    INSERT INTO {} (id, source_url, language, updated_on, title, description, section, html, content, related_links)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                    ON CONFLICT (id) DO NOTHING;
                    """
                ).format(self.documents_table_identifier),
                [
                    (
                        document.id,
                        document.source_url,
                        document.language,
                        document.updated_on,
                        document.title,
                        document.description,
                        document.section,
                        document.html,
                        document.content,
                        document.related_links
                    )
                    for document in batch if document.content
                ],
                returning=True
            )
            self.logger.info(f"Upserted {len(batch)} document records.)")


            # SPLIT DOCUMENTS INTO CHUNKS AND GENERATE EMBEDDINGS
            chunked_batch = self.chunk_batch(batch, 300, 50) # list of dictionaries

            batch_texts = [f"Document: {chunk["title"]}\nSection: {chunk["section"]}\n\n{chunk['content']}" for chunk in chunked_batch]
            embeddings = self.embedder.encode_batch(batch_texts)

            # UPLOAD CHUNKS
            self.cur.executemany(
                sql.SQL(
                    """
                    INSERT INTO {} (document_id, chunk_id, content, embedding)
                    VALUES (%s, %s, %s, %s)
                    ON CONFLICT (document_id, chunk_id) DO NOTHING;
                    """
                ).format(self.chunks_table_identifier),
                [
                    (
                        chunk["document_id"],
                        chunk["chunk_id"],
                        chunk["content"],
                        vec_to_str(embeddings[i]),
                    )
                    for i, chunk in enumerate(chunked_batch) if chunk["content"]
                ],
                returning=True
            )
            self.logger.info(f"Upserted {len(chunked_batch)} chunk records.)")
        except Exception as e:
            self.con.rollback()
            self.logger.error(f"Error writing batch data: {e}")
            raise


    def vector_search(self, query, num_results=5):
        try:
            query_vector = self.embedder.encode(query)
            query_str = vec_to_str(query_vector)

            return self.cur.execute(
                sql.SQL(
                    """
                    SELECT d.title, d.section, c.content, d.source_url
                    FROM {} c
                    JOIN {} d
                    ON c.document_id = d.id
                    ORDER BY c.embedding <=> %s::vector
                    LIMIT %s
                    """
                ).format(self.chunks_table_identifier, self.documents_table_identifier),
                (query_str, num_results)
            ).fetchall()
        except Exception as e:
            self.logger.error(f"Unable to fetch results: {e}")


    def copy_table_to_csv(self, dest="data"):
        dest = PROJECT_ROOT / dest
        dest.mkdir(parents=True, exist_ok=True)

        try:
            with open(dest / "chunks.csv", "wb") as f:
                with self.cur.copy(
                    sql.SQL("COPY (SELECT * FROM {}) TO STDOUT WITH CSV HEADER").format(self.chunks_table_identifier)
                ) as copy:
                    while data := copy.read():
                        f.write(data)
            self.logger.info(f"Table data copied to {dest}/chunks.csv")

            with open(dest / "documents.csv", "wb") as f:
                with self.cur.copy(
                    sql.SQL("COPY (SELECT * FROM {}) TO STDOUT WITH CSV HEADER").format(self.documents_table_identifier)
                ) as copy:
                    while data := copy.read():
                        f.write(data)
            self.logger.info(f"Table data copied to {dest}/documents.csv")
        except Exception as e:
            self.logger.error("Error copying the data to the file: {}".format(e))