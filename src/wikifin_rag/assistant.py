import sys
import streamlit as st
from openai import OpenAI
import pickle
from wikifin_rag.config import PROJECT_ROOT
from wikifin_rag.search_utils import load_text_index, load_vector_index, vector_search, text_search, rrf_hybrid_search
from wikifin_rag.rag_helper import RAGBase
from wikifin_rag.db_client import MonitoringDBClient
from wikifin_rag.embedder import Embedder
import pickle

def ts_function(query):
    with open(PROJECT_ROOT / "data" / "evals" / "ts_index_params.pkl", "rb") as file:
        ts_params = pickle.load(file)

    ts_index = load_text_index()
    return text_search(query=query, index=ts_index, boost_dict=ts_params)


def vs_function(query):
    embedder = Embedder()

    with open(PROJECT_ROOT / "data" / "evals" / "vs_index_params.pkl", "rb") as file:
        vs_params = pickle.load(file)

    vs_index = load_vector_index(**vs_params)
    return vector_search(query=query, index=vs_index, embedder=embedder)


def hs_function(query):
    vs_results = vs_function(query)
    ts_results = ts_function(query)

    return rrf_hybrid_search([vs_results, ts_results])


def create_assistant():
    return RAGBase(
        search_function=vs_function,
        llm_client=OpenAI(api_key=st.secrets["OPENAI_API_KEY"]),
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