from itemadapter import ItemAdapter
from wikifin_rag.ingest import get_db_connection
from psycopg import sql

class SQLiteUploadPipeline:
    collection_name = "document_chunks"

    def __init__(self):
        self.con = get_db_connection()
        self.cur = self.con.cursor()
        self.table_identifier = sql.Identifier(self.collection_name)

    def open_spider(self):
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

    def close_spider(self):
        self.con.commit()
        self.cur.close()
        self.con.close()

    def process_item(self, item):
        adapter = ItemAdapter(item)

        self.cur.execute(
            sql.SQL(
                """
                INSERT INTO {} (chunk_id, source_url, language, date, category, description, title, html, content, related_links)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                ON CONFLICT (chunk_id) DO NOTHING;
                """
            ).format(self.table_identifier),
            (
                adapter.get("chunk_id"),
                adapter.get("source_url"),
                adapter.get("language"),
                adapter.get("date"),
                adapter.get("category"),
                adapter.get("description"),
                adapter.get("title"),
                adapter.get("html"),
                adapter.get("content"),
                adapter.get("related_links")
            )
        )

        return "New row inserted in the DB"