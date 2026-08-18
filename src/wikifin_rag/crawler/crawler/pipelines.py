from wikifin_rag.db_client import DBClient

class PostgresUpload:
    collection_name = "document_chunks"

    def __init__(self):
        self.db_client = DBClient(table_name=self.collection_name)

    def open_spider(self):
        self.db_client.open_connection()
        self.db_client.create_table(drop=False)

    def close_spider(self):
        self.db_client.close_connection()

    def process_item(self, item):
        if len(item) == 0:
            return "No elements in the batch."

        affected_batches = self.db_client.insert_batch(item)
        return f"Upserted {affected_batches} batch ({len(item)} rows)."