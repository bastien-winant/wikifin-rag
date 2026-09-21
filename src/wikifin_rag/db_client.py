import logging
from wikifin_rag.config import PROJECT_ROOT
from pathlib import Path
import json
import sqlite3
from wikifin_rag.embedder import Embedder
from wikifin_rag.utils import chunk_document_batch
from datetime import datetime, date
from wikifin_rag.factories import record_factory, stats_factory


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

    def insert_batch(self, batch):
        try:
            with self.get_db_connection() as con:
                cur = con.cursor()

                cur.executemany(f"""
                    INSERT INTO {self.documents_table_identifier} (id, source_url, language, updated_on, title, description, section, html, content, related_links)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    ON CONFLICT (id) DO NOTHING;
                    """,
                    [
                        (
                            document.id,
                            document.source_url,
                            document.language,
                            document.updated_on.strftime(format='%Y-%m-%d %H:%M:%S.%f'),
                            document.title,
                            document.description,
                            document.section,
                            document.html,
                            document.content,
                            json.dumps(document.related_links)
                        )
                        for document in batch if document.content
                    ]
                )
                self.logger.info(f"Upserted {len(batch)} document records.")


                # SPLIT DOCUMENTS INTO CHUNKS AND GENERATE EMBEDDINGS
                chunked_batch = chunk_document_batch(batch, 1200, 250)

                batch_texts = [f"Document: {chunk['title']}\nSection: {chunk['section']}\n\n{chunk['content']}" for chunk in chunked_batch]
                embeddings = self.embedder.encode_batch(batch_texts)

                cur.executemany(f"""
                    INSERT INTO {self.chunks_table_identifier} (document_id, chunk_id, content, embedding)
                    VALUES (?, ?, ?, ?)
                    ON CONFLICT (document_id, chunk_id) DO NOTHING;
                    """,
                    [
                        (
                            chunk["document_id"],
                            chunk["chunk_id"],
                            chunk["content"],
                            embeddings[i].tobytes(),
                        )
                        for i, chunk in enumerate(chunked_batch) if chunk["content"]
                    ]
                )
                self.logger.info(f"Upserted {len(chunked_batch)} chunk records.")
        except Exception as e:
            self.logger.error(f"Error writing batch data: {e}")
            raise


class MonitoringDBClient(DBClient):
    def __init__(self, db_path=PROJECT_ROOT / "db" / "wikifin_rag.db"):
        super().__init__(db_path=db_path)

        self.conversations_table_identifier = "conversations"
        self.feedback_table_identifier = "feedback"

    def init_db(self, drop=False):
        try:
            with self.get_db_connection() as con:
                cur = con.cursor()

                if drop:
                    cur.execute(f"DROP TABLE IF EXISTS {self.conversations_table_identifier};")
                    cur.execute(f"DROP TABLE IF EXISTS {self.feedback_table_identifier};")

                cur.execute(f"""
                    CREATE TABLE IF NOT EXISTS {self.conversations_table_identifier} (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        query TEXT NOT NULL,
                        answer TEXT NOT NULL,
                        model TEXT NOT NULL,
                        instructions TEXT NOT NULL,
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
                        conversation_id INTEGER REFERENCES conversations(id),
                        source TEXT NOT NULL,
                        relevance TEXT,
                        explanation TEXT,
                        score INTEGER,
                        timestamp TEXT NOT NULL DEFAULT current_timestamp
                    )
                """)

                self.logger.info("Database initialized")
        except Exception as e:
            self.logger.error(f"The tables could not be created: {e}")
            raise

    def save_conversation(self, record, query):
        try:
            timestamp = datetime.now(self.DB_TIMEZONE).strftime(format='%Y-%m-%d %H:%M:%S.%f')

            with self.get_db_connection() as con:
                cur = con.execute(f"""
                    INSERT INTO {self.conversations_table_identifier} (
                        query, answer, model, instructions, prompt,
                        prompt_tokens, completion_tokens, total_tokens,
                        response_time, input_cost, output_cost, total_cost, timestamp
                    ) VALUES (
                        ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?
                    )
                    RETURNING id;
                    """,
                    (
                        query,
                        record.answer,
                        record.model,
                        record.instructions,
                        record.prompt,
                        record.prompt_tokens,
                        record.completion_tokens,
                        record.total_tokens,
                        record.response_time,
                        record.input_cost,
                        record.output_cost,
                        record.total_cost,
                        timestamp,
                    ),
                )
                conversation_id = cur.fetchone()[0]

                self.logger.info(f"Inserted new LLM conversation record.")
        except Exception as e:
            self.logger.error(f"Error writing conversation data: {e}")
            raise

        return conversation_id

    def save_feedback(self, conversation_id, source, relevance=None, explanation=None, score=None):
        timestamp = datetime.now(self.DB_TIMEZONE)

        try:
            with self.get_db_connection() as con:
                con.execute(
                    """
                    INSERT INTO feedback (
                        conversation_id, source, relevance,
                        explanation, score, timestamp
                    ) VALUES (
                        ?, ?, ?, ?, ?, ?
                    )
                    """,
                    (conversation_id, source, relevance,
                    explanation, score, timestamp),
                )
        except Exception as e:
            self.logger.error(f"Error writing feedback data: {e}")
            raise

    def get_conversations(self, limit=10):
        try:
            with self.get_db_connection() as con:
                con.row_factory = record_factory

                cur = con.execute(
                    """
                    SELECT id, query, answer, model,
                        instructions, prompt,
                        prompt_tokens, completion_tokens, total_tokens,
                        response_time, input_cost, output_cost, total_cost, timestamp
                    FROM conversations
                    ORDER BY timestamp DESC
                    LIMIT ?
                    """,
                    (limit,),
                )
                rows = cur.fetchall()
        except Exception as e:
            self.logger.error(f"Error retrieving the data: {e}")
            raise

        return rows

    def get_conversation_stats(self):
        try:
            with self.get_db_connection() as con:
                con.row_factory = stats_factory

                cur = con.execute(f"""
                    SELECT
                        COUNT(*),
                        AVG(response_time),
                        SUM(total_cost),
                        AVG(total_tokens)
                    FROM {self.conversations_table_identifier}
                """)
                row = cur.fetchone()
        except Exception as e:
            self.logger.error(f"Error retrieving the data: {e}")
            raise

        return row

    def get_relevance_stats(self):
        try:
            with self.get_db_connection() as con:
                cur = con.execute(f"""
                    SELECT relevance, COUNT(*)
                    FROM {self.feedback_table_identifier}
                    WHERE source = 'judge'
                    GROUP BY relevance
                """)
                rows = cur.fetchall()
        except Exception as e:
            self.logger.error(f"Error retrieving the data: {e}")
            raise

        return dict(rows)

    def get_user_feedback_stats(self):
        try:
            with self.get_db_connection() as con:
                cur = con.execute(f"""
                    SELECT
                        SUM(CASE WHEN score > 0 THEN 1 ELSE 0 END),
                        SUM(CASE WHEN score < 0 THEN 1 ELSE 0 END)
                    FROM {self.feedback_table_identifier}
                    WHERE source = 'user'
                """)
                row = cur.fetchone()
        except Exception as e:
            self.logger.error(f"Error retrieving the data: {e}")
            raise

        return row