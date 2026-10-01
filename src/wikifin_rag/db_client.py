import logging
from wikifin_rag.config import PROJECT_ROOT
from pathlib import Path
import sqlite3
from wikifin_rag.embedder import Embedder
from datetime import datetime, date


dest = PROJECT_ROOT / "logs" / "db"
dest.mkdir(parents=True, exist_ok=True)

LOG_FILENAME = f"{date.today().strftime("%d_%m_%y")}.log"

fh = logging.FileHandler(dest / LOG_FILENAME)
fh.setLevel(logging.WARNING)
formatter = logging.Formatter("%(asctime)s - %(levelname)s - %(message)s")
fh.setFormatter(formatter)


class DBClient():
    def __init__(self, db_path):
        self.db_path = Path(db_path)

        self.logger = logging.getLogger(__name__)
        self.logger.addHandler(fh)

        self.DB_TIMEZONE = datetime.now().astimezone().tzinfo


    def get_db_connection(self, autocommit=True):
        try:
            self.db_path.parent.mkdir(parents=True, exist_ok=True)
            return sqlite3.connect(self.db_path, autocommit=autocommit)
        except Exception:
            self.logger.exception("Unable to open the database connection")
            raise


class DocumentsDBClient(DBClient):
    def __init__(self, db_path=PROJECT_ROOT / "db" / "wikifin_rag.db", embedder=Embedder()):
        super().__init__(db_path=db_path)

        self.documents_table_identifier = "documents"
        self.chunks_table_identifier = "chunks"

        self.embedder = embedder

    def init_db(self, drop=False):
        try:
            with self.get_db_connection() as con:
                cur = con.cursor()

                if drop:
                    cur.execute(f"DROP TABLE IF EXISTS {self.chunks_table_identifier};")
                    cur.execute(f"DROP TABLE IF EXISTS {self.documents_table_identifier};")

                cur.execute(f"""
                    CREATE TABLE IF NOT EXISTS {self.documents_table_identifier} (
                        id TEXT PRIMARY KEY,
                        source_url TEXT NOT NULL,
                        language TEXT,
                        updated_on TEXT,
                        title TEXT,
                        description TEXT,
                        section TEXT,
                        html TEXT,
                        content TEXT,
                        related_links TEXT,
                        updated_at TEXT NOT NULL DEFAULT current_timestamp
                    );
                """)

                cur.execute(f"""
                    CREATE TABLE IF NOT EXISTS {self.chunks_table_identifier} (
                        document_id TEXT REFERENCES {self.documents_table_identifier} (id),
                        chunk_id TEXT NOT NULL,
                        content TEXT,
                        embedding BLOB,
                        updated_at TEXT NOT NULL DEFAULT current_timestamp,
                        PRIMARY KEY (document_id, chunk_id)
                    );
                """)

                self.logger.info("Database initialized")
        except Exception as e:
            self.logger.error(f"The tables could not be created: {e}")
            raise


class MonitoringDBClient(DBClient):
    def __init__(self, db_path=PROJECT_ROOT / "db" / "wikifin_traces.db"):
        super().__init__(db_path=db_path)

        self.conversations_table_identifier = "conversations"
        self.exchanges_table_identifier = "exchanges"
        self.feedback_table_identifier = "feedback"

    def init_db(self, drop=False):
        try:
            with self.get_db_connection() as con:
                cur = con.cursor()

                if drop:
                    cur.execute(f"DROP TABLE IF EXISTS {self.conversations_table_identifier};")
                    cur.execute(f"DROP TABLE IF EXISTS {self.exchanges_table_identifier};")
                    cur.execute(f"DROP TABLE IF EXISTS {self.feedback_table_identifier};")

                cur.execute(f"""
                    CREATE TABLE IF NOT EXISTS {self.conversations_table_identifier} (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        model TEXT NOT NULL,
                        instructions TEXT NOT NULL,
                        started_at TEXT NOT NULL DEFAULT current_timestamp
                    );
                """)

                cur.execute(f"""
                    CREATE TABLE IF NOT EXISTS {self.exchanges_table_identifier} (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        conversation_id INTEGER REFERENCES {self.conversations_table_identifier}(id),
                        query TEXT NOT NULL,
                        answer TEXT NOT NULL,
                        prompt TEXT NOT NULL,
                        prompt_tokens INTEGER NOT NULL,
                        completion_tokens INTEGER NOT NULL,
                        total_tokens INTEGER NOT NULL,
                        response_time REAL NOT NULL,
                        input_cost REAL NOT NULL,
                        output_cost REAL NOT NULL,
                        total_cost REAL NOT NULL,
                        timestamp TEXT NOT NULL DEFAULT current_timestamp
                    );
                """)

                cur.execute(f"""
                    CREATE TABLE IF NOT EXISTS {self.feedback_table_identifier} (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        exchange_id INTEGER REFERENCES {self.exchanges_table_identifier}(id),
                        source TEXT NOT NULL,
                        relevance TEXT,
                        explanation TEXT,
                        score INTEGER,
                        timestamp TEXT NOT NULL DEFAULT current_timestamp
                    );
                """)

                self.logger.info("Database initialized")
        except Exception as e:
            self.logger.error(f"The tables could not be created: {e}")
            raise