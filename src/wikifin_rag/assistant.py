from dotenv import load_dotenv
from openai import OpenAI
from wikifin_rag.rag_helper import RAGBase
from wikifin_rag.embedder import Embedder
from wikifin_rag.db_client import PostgresClient
import sys

def search_function(query):
    embedder = Embedder()
    db_client = PostgresClient(embedder=embedder)
    db_client.open_connection()

    results = db_client.vector_search(query=query, num_results=5)

    db_client.close_connection()

    return results

def create_assistant():
    load_dotenv(override=True)
    openai_client = OpenAI()
    assistant = RAGBase(llm_client=openai_client)

    return assistant

if __name__ == "__main__":
    assistant = create_assistant()

    query = "What is an insurance contract?"

    if len(sys.argv) > 1:
        query = sys.argv[1]

    answer = assistant.rag(query=query, search_function=search_function)
    print(answer)
    