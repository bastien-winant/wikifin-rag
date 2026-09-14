from wikifin_rag.db_client import DocumentsDBClient
from sqlitesearch import TextSearchIndex, VectorSearchIndex
from wikifin_rag.config import PROJECT_ROOT
from wikifin_rag.factories import dict_factory


def load_wikifin_data(factory=dict_factory):
    db_client = DocumentsDBClient()

    with db_client.get_db_connection() as con:
        con.row_factory = factory

        cur = con.execute("""
            SELECT
                c.document_id || '_' || c.chunk_id AS id,
                d.title,
                d.section,
                c.content,
                c.embedding,
                d.source_url
            FROM chunks c
            JOIN documents d
            ON c.document_id = d.id
            WHERE d.language = 'nl';
        """)

    return cur.fetchall()


def build_text_index(documents):
    index = TextSearchIndex(
        text_fields=['title', 'section', 'content'],
        db_path=PROJECT_ROOT / "db" / "sqlitesearch_text.db",
    )

    index.clear()
    index.fit(documents)
    return index


def build_vector_index(vectors, documents, **kwargs):
    index = VectorSearchIndex(
        db_path=PROJECT_ROOT / "db" / "sqlitesearch_vectors.db",
        **kwargs
    )
    
    index.clear()
    index.fit(vectors, documents)
    return index
