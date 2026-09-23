import streamlit as st
import time
from wikifin_rag.assistant import create_assistant
from wikifin_rag.db_client import MonitoringDBClient
from wikifin_rag.judge import evaluate_relevance


assistant = create_assistant()

db_client = MonitoringDBClient()
db_client.init_db()


def save_feedback():
    conversation_id = st.session_state.conversation_id
    db_client.save_feedback(conversation_id, "user", score=st.session_state[f"feedback_{conversation_id}"])


st.title("Ask Wik:blue[i]f:green[i]n")
container = st.container(border=True, height=300)


if prompt := st.chat_input("Say something"):
    st.session_state.prompt = prompt


if "prompt" in st.session_state:
    container.chat_message("user").write(prompt)

    if "response" not in st.session_state:
        response = assistant.rag(prompt)
        st.session_state.response = response

        record = assistant.last_call
        conversation_id = db_client.save_conversation(record, prompt)
        st.session_state.conversation_id = conversation_id

        # generate and save LLM-as-judge feedback
        relevance, explanation = evaluate_relevance(prompt, response)
        db_client.save_feedback(conversation_id, "judge", relevance=relevance, explanation=explanation)

    with container.chat_message("assistant"):
        response = st.session_state.response
        conversation_id = st.session_state.conversation_id

        st.write(response)

        # listen for user feedback
        st.feedback(
            "thumbs",
            key=f"feedback_{conversation_id}",
            on_change=save_feedback,
        )