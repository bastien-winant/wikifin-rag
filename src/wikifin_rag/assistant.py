import sys

from dotenv import load_dotenv
from openai import OpenAI

from wikifin_rag.ingest import load_wikifin_data, build_text_index, build_vector_index
from wikifin_rag.rag_helper import RAGBase
from wikifin_rag.db_client import MonitoringDBClient

def create_assistant():
    load_dotenv(override=True)

    documents = load_wikifin_data()
    index = build_text_index(documents)

    return RAGBase(
        index=index,
        llm_client=OpenAI(),
    )


if __name__ == "__main__":
    assistant = create_assistant()
    
    db_client = MonitoringDBClient()
    db_client.init_db(drop=True)

    query = "Hoe zich beschermen tegen fraude?"
    if len(sys.argv) > 1:
        query = sys.argv[1]

    answer = assistant.rag(query)
    db_client.save_conversation(record=assistant.last_call, query=query)
    print(answer)