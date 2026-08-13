from itemadapter import ItemAdapter
from wikifin_rag.ingest import get_db_connection


class SQLiteUploadPipeline:
    collection_name = "documents"

    def __init__(self):
        self.con = get_db_connection()
        self.cur = self.con.cursor()

    def open_spider(self):
        self.cur.execute("CREATE EXTENSION IF NOT EXISTS vector;")

        self.cur.execute(
            f"""CREATE TABLE IF NOT EXISTS {self.collection_name} (
                source_url TEXT PRIMARY KEY,
                language TEXT,
                title TEXT,
                description TEXT,
                date TEXT,
                html TEXT,
                embedding vector(768),
                related_links TEXT[]
            );"""
        )

        self.cur.execute(f"""
            CREATE INDEX ON {self.collection_name}
            USING hnsw (embedding vector_cosine_ops)
        """)

    def close_spider(self):
        self.con.commit()
        self.cur.close()
        self.con.close()

    def process_item(self, item):
        adapter = ItemAdapter(item)
        
        self.cur.execute(
            f"""INSERT INTO {self.collection_name} (source_url, language, title, description, date, html, related_links)
                VALUES (%s, %s, %s, %s, %s, %s, %s)
                ON CONFLICT (source_url) DO NOTHING;
            """,
            (
                adapter.get("source_url"),
                adapter.get("language"),
                adapter.get("title"),
                adapter.get("description"),
                adapter.get("date"),
                adapter.get("html"),
                adapter.get("related_urls")
            )
        )

        return "New row inserted in the DB"