from wikifin_rag.db_client import DocumentsDBClient
from wikifin_rag.utils import chunk_document_batch
import json

def insert_batch(batch):
        db_client = DocumentsDBClient()

        try:
            with db_client.get_db_connection() as con:
                cur = con.cursor()

                cur.executemany(f"""
                    INSERT INTO {db_client.documents_table_identifier} (id, source_url, language, updated_on, title, description, section, html, content, related_links)
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
                db_client.logger.info(f"Upserted {len(batch)} document records.")


                # SPLIT DOCUMENTS INTO CHUNKS AND GENERATE EMBEDDINGS
                chunked_batch = chunk_document_batch(batch, 1200, 250)

                batch_texts = [f"Document: {chunk['title']}\nSection: {chunk['section']}\n\n{chunk['content']}" for chunk in chunked_batch]
                embeddings = db_client.embedder.encode_batch(batch_texts)

                cur.executemany(f"""
                    INSERT INTO {db_client.chunks_table_identifier} (document_id, chunk_id, content, embedding)
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
                db_client.logger.info(f"Upserted {len(chunked_batch)} chunk records.")
        except Exception as e:
            db_client.logger.error(f"Error writing batch data: {e}")
            raise