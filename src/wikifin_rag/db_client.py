import logging
from wikifin_rag.config import PROJECT_ROOT
from datetime import date
from dotenv import load_dotenv
import os
from psycopg import connect, sql, rows
from wikifin_rag.embedder import Embedder
from wikifin_rag.utils import vec_to_str, chunk_document_batch, rrf

dest = PROJECT_ROOT / "logs"
dest.mkdir(parents=True, exist_ok=True)

# LOG_FILENAME = 'db_logs.log'
LOG_FILENAME = f"db_logs__{date.today().strftime("%d_%m_%y")}.log"

fh = logging.FileHandler(PROJECT_ROOT / "logs" / LOG_FILENAME)
fh.setLevel(logging.WARNING)
formatter = logging.Formatter("%(asctime)s - %(levelname)s - %(message)s")
fh.setFormatter(formatter)


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
        self.logger.addHandler(fh)


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
            self.logger.info(f"Upserted {len(batch)} document records.")


            # SPLIT DOCUMENTS INTO CHUNKS AND GENERATE EMBEDDINGS
            chunked_batch = chunk_document_batch(batch, 300, 50)

            batch_texts = [f"Document: {chunk['title']}\nSection: {chunk['section']}\n\n{chunk['content']}" for chunk in chunked_batch]
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
            self.logger.info(f"Upserted {len(chunked_batch)} chunk records.")
        except Exception as e:
            self.con.rollback()
            self.logger.error(f"Error writing batch data: {e}")
            raise

    
    def text_search(self, query, weights=None, normalization=0, num_results=5):
        try:
            weight_values = [0.1, 0.2, 0.4, 1.0]

            if type(weights) == dict and set(weights.keys()) == {'title_weight', 'description_weight', 'section_weight', 'content_weight'}:
                weight_values = [
                    weights["title_weight"],
                    weights["description_weight"],
                    weights["section_weight"],
                    weights["content_weight"]
                ]

            return self.cur.execute(
                sql.SQL(
                    """
                    WITH textsearch_vector AS (
                        SELECT
                            c.document_id || '_' || c.chunk_id AS id,
                            d.title,
                            d.section,
                            c.content,
                            d.source_url,
                            setweight(to_tsvector(coalesce(d.title, '')), 'A') ||
                                setweight(to_tsvector(coalesce(d.description, '')), 'B') ||
                                setweight(to_tsvector(coalesce(d.section, '')), 'C') ||
                                setweight(to_tsvector(coalesce(c.content, '')), 'D') AS ts_vector
                        FROM {} c
                        JOIN {} d
                        ON c.document_id = d.id
                        WHERE d.language = %s
                    ),
                    query AS (SELECT plainto_tsquery(%s) AS ts_query)
                    SELECT
                        id,
                        title,
                        section,
                        content,
                        source_url
                    FROM textsearch_vector, query
                    ORDER BY ts_rank(%s::real[], ts_vector, ts_query, %s) DESC
                    LIMIT %s
                    """
                ).format(self.chunks_table_identifier, self.documents_table_identifier),
                ("nl", query, weight_values, normalization, num_results)
            ).fetchall()
        except Exception as e:
            self.logger.error(f"Unable to fetch results: {e}")


    def vector_search(self, query, num_results=5):
        try:
            query_vector = self.embedder.encode(query)
            query_str = vec_to_str(query_vector)

            return self.cur.execute(
                sql.SQL(
                    """
                    SELECT
                        c.document_id || '_' || c.chunk_id AS id,
                        d.title,
                        d.section,
                        c.content,
                        d.source_url
                    FROM {} c
                    JOIN {} d
                    ON c.document_id = d.id
                    WHERE d.language = %s
                    ORDER BY c.embedding <=> %s::vector
                    LIMIT %s
                    """
                ).format(self.chunks_table_identifier, self.documents_table_identifier),
                ("nl", query_str, num_results)
            ).fetchall()
        except Exception as e:
            self.logger.error(f"Unable to fetch results: {e}")


    def hybrid_search(self, query, weights=None, normalization=0, num_results=5):
        try:
            text_search_results = self.text_search(query=query, weights=weights, normalization=normalization, num_results=num_results)
            vector_search_results = self.vector_search(query=query, num_results=num_results)
            return rrf([text_search_results, vector_search_results], num_results=num_results)
        except Exception as e:
            self.logger.error(f"Unable to fetch results: {e}")