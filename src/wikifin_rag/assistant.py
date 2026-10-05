import sys
import json
import streamlit as st
from openai import OpenAI
from wikifin_rag.config import PROJECT_ROOT
from wikifin_rag.search_utils import load_text_index, load_vector_index, vector_search, text_search, rrf_hybrid_search
from wikifin_rag.rag_helper import RAGBase
from wikifin_rag.db_client import MonitoringDBClient
from wikifin_rag.embedder import Embedder

with open(PROJECT_ROOT / "config" / "search_params.json", encoding="utf-8") as file:
    SEARCH_PARAMS = json.load(file)


@st.cache_resource
def get_embedder() -> Embedder:
    return Embedder()


@st.cache_resource
def get_text_index():
    return load_text_index()


@st.cache_resource
def get_vector_index():
    return load_vector_index(**SEARCH_PARAMS["vector"])


def ts_function(query):
    ts_index = get_text_index()
    return text_search(query=query, index=ts_index, boost_dict=SEARCH_PARAMS["text"])


def vs_function(query):
    embedder = get_embedder()
    vs_index = get_vector_index()
    return vector_search(query=query, index=vs_index, embedder=embedder)


def hs_function(query):
    vs_results = vs_function(query)
    ts_results = ts_function(query)

    return rrf_hybrid_search([vs_results, ts_results])


@st.cache_resource
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