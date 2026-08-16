from dotenv import load_dotenv
import os
from psycopg import connect, sql
from dataclasses import astuple

class DBClient():
    def __init__(self, table_name="document_chunks"):
        load_dotenv(override=True)

        self.table_identifier = sql.Identifier(table_name)

        self.db_host = "localhost"
        self.db_port = 5432
        self.db_name = os.environ['POSTGRES_DB']
        self.db_user = os.environ['POSTGRES_USER']
        self.db_password = os.environ['POSTGRES_PASSWORD']

    def open_connection(self, autocommit=True):
        try:
            self.con = connect(
                host=self.db_host,
                port=self.db_port,
                dbname=self.db_name,
                user=self.db_user,
                password=self.db_password,
                autocommit=autocommit
            )

            self.cur = self.con.cursor()
        except:
            print("Unable to open database connection.")

    def close_connection(self):
        try:
            self.cur.close()
            self.con.close()
            self.con.close()
        except:
            print("Unable to close database connection.")

    def create_table(self, drop=False):
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
                    date TEXT,
                    category TEXT,
                    description TEXT,
                    title TEXT,
                    html TEXT,
                    content TEXT,
                    embedding vector(768),
                    related_links TEXT[]
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


    def insert_batch(self, batch):
        self.cur.executemany(
            sql.SQL(
                """
                INSERT INTO {} (chunk_id, source_url, language, date, category, description, title, html, content, related_links)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                ON CONFLICT (chunk_id) DO NOTHING;
                """
            ).format(self.table_identifier),
            [astuple(chunk) for chunk in batch.chunks],
            returning=True
        )

        return self.cur.rowcount