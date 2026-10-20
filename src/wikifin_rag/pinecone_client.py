import logging
import os
import time
from datetime import date, datetime

from dotenv import load_dotenv
from pinecone import Pinecone, SchemaBuilder

from wikifin_rag.config import EMBED_DIM, INDEX_NAME, PROJECT_ROOT

load_dotenv(override=True)

_logger = logging.getLogger(__name__)
try:
    _log_dir = PROJECT_ROOT / "logs" / "db"
    _log_dir.mkdir(parents=True, exist_ok=True)
    _fh = logging.FileHandler(_log_dir / f"{date.today().strftime('%d_%m_%y')}.log")
    _fh.setLevel(logging.WARNING)
    _fh.setFormatter(logging.Formatter("%(asctime)s - %(levelname)s - %(message)s"))
    _logger.addHandler(_fh)
except OSError:
    _logger.addHandler(logging.NullHandler())


class PineconeClient:
    def __init__(self):
        self.logger = _logger

        self.DB_TIMEZONE = datetime.now().astimezone().tzinfo

        self._pc = Pinecone(api_key=os.environ["PINECONE_API_KEY"])

    def _build_schema(self, embed_dim: int, metric: str):
        return (
            SchemaBuilder()
            .add_string_field(name="title", full_text_search={"language": "nl"})
            .add_string_field(
                name="description",
                full_text_search={"language": "nl", "stemming": True, "stop_words": True},
            )
            .add_string_field(name="section", full_text_search={"language": "nl"})
            .add_string_field(
                name="text",
                full_text_search={"language": "nl", "stemming": True, "stop_words": True},
            )
            .add_dense_vector_field(name="embedding", dimension=embed_dim, metric=metric)
            .build()
        )

    def ensure_index(
        self,
        name: str = INDEX_NAME,
        embed_dim: int = EMBED_DIM,
        metric: str = "cosine",
        recreate: bool = False,
    ):
        try:
            if recreate and self._pc.indexes.exists(name=name):
                self._pc.delete_index(name)

                while self._pc.indexes.exists(name=name):
                    time.sleep(2)

            if not self._pc.indexes.exists(name=name):
                schema = self._build_schema(embed_dim=embed_dim, metric=metric)
                self._pc.indexes.create(name=name, schema=schema)

            while not self._pc.indexes.describe(name=name).status.ready:
                time.sleep(2)
        except Exception as e:
            self.logger.error(f"The tables could not be created: {e}")
            raise

    def get_index(self, name: str = INDEX_NAME):
        try:
            return self._pc.Index(name)
        except Exception as e:
            self.logger.error(f"The tables could not be created: {e}")
            raise

    def close_pc_connection(self):
        try:
            self._pc.close()
        except Exception as e:
            self.logger.exception(e)
            raise
