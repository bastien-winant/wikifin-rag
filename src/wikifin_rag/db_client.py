from dotenv import load_dotenv
import os
from psycopg import connect, sql, rows
from dataclasses import astuple
from wikifin_rag.embedder import Embedder
from wikifin_rag.config import PROJECT_ROOT
from wikifin_rag.utils import vec_to_str
import logging


class PostgresClient():
    def __init__(self, table_name="document_chunks", embedder=Embedder()):
        load_dotenv(override=True)

        self.table_identifier = sql.Identifier(table_name)

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


    def create_table(self, drop=False):
        try:
            if drop:
                self.cur.execute(
                    sql.SQL("DROP TABLE IF EXISTS {};").format(self.table_identifier)
                )

            self.cur.execute("CREATE EXTENSION IF NOT EXISTS vector;")
            
            self.cur.execute(
                sql.SQL(
                    """
                    CREATE TABLE IF NOT EXISTS {} (
                        chunk_id TEXT PRIMARY KEY,
                        source_url TEXT NOT NULL,
                        language TEXT,
                        updated_on DATE,
                        category TEXT,
                        description TEXT,
                        title TEXT,
                        html TEXT,
                        content TEXT,
                        embedding vector(768),
                        related_links TEXT[],
                        updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
                    );
                    """
                ).format(self.table_identifier)
            )

            self.cur.execute(
                sql.SQL(
                    """
                    CREATE INDEX ON {}
                    USING hnsw (embedding vector_cosine_ops)
                    """
                ).format(self.table_identifier)
            )

            self.logger.info("The database table has been created.")

        except Exception as e:
            self.logger.error(f"The table could not be created: {e}")


    def insert_batch(self, batch):
        batch_texts = [f"{chunk.title}\n{chunk.content}" for chunk in batch]
        embeddings = self.embedder.encode_batch(batch_texts)

        try:
            self.cur.executemany(
                sql.SQL(
                    """
                    INSERT INTO {} (chunk_id, source_url, language, updated_on, category, description, title, html, content, related_links, embedding)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                    ON CONFLICT (chunk_id) DO NOTHING;
                    """
                ).format(self.table_identifier),
                [astuple(batch[i]) + (vec_to_str(embeddings[i]),) for i in range(len(batch))],
                returning=True
            )
            self.con.commit()
            self.logger.info(f"Upserted the batch ({len(batch)} records.)")
            return self.cur.rowcount
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
                    SELECT category, title, content, source_url
                    FROM {}
                    ORDER BY embedding <=> %s::vector
                    LIMIT %s
                    """
                ).format(self.table_identifier),
                (query_str, num_results)
            ).fetchall()
        except Exception as e:
            self.logger.error(f"Unable to fetch results: {e}")


    def copy_table_to_csv(self, filename, dest="data"):
        dest = PROJECT_ROOT / dest
        dest.mkdir(parents=True, exist_ok=True)

        try:
            with open(dest / filename, "wb") as f:
                with self.cur.copy(
                    sql.SQL("COPY (SELECT * FROM {}) TO STDOUT WITH CSV HEADER").format(self.table_identifier)
                ) as copy:
                    while data := copy.read():
                        f.write(data)
            self.logger.info(f"Table data copied to {dest / filename}")
        except Exception as e:
            self.logger.error("Error copying the data to the file: {}".format(e))