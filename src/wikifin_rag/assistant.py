from dotenv import load_dotenv
from openai import OpenAI
from wikifin_rag.rag_helper import RAGBase
from wikifin_rag.embedder import Embedder
from wikifin_rag.db_client import DocumentsClient


def search_function(query):
    embedder = Embedder()
    db_client = DocumentsClient(embedder=embedder)
    db_client.open_connection()

    results = db_client.vector_search(query=query, num_results=5)

    db_client.close_connection()

    return results


def create_assistant():
    load_dotenv(override=True)
    openai_client = OpenAI()
    assistant = RAGBase(llm_client=openai_client)

    return assistant