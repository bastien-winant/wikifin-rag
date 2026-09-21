import streamlit as st
import time
from wikifin_rag.assistant import create_assistant
from wikifin_rag.db_client import MonitoringDBClient
from wikifin_rag.judge import evaluate_relevance


assistant = create_assistant()

db_client = MonitoringDBClient()
db_client.init_db(drop=False)


def chat_stream(prompt):
    response = assistant.rag(prompt)
    return response


def save_feedback(index):
    st.session_state.history[index]["feedback"] = st.session_state[f"feedback_{index}"]


if "history" not in st.session_state:
    st.session_state.history = []


st.title("Ask Wik:blue[i]f:green[i]n")

for i, message in enumerate(st.session_state.history):
    with st.chat_message(message["role"]):
        st.write(message["content"])
        if message["role"] == "assistant":
            feedback = message.get("feedback", None)
            st.session_state[f"feedback_{i}"] = feedback
            st.feedback(
                "thumbs",
                key=f"feedback_{i}",
                disabled=feedback is not None,
                on_change=save_feedback,
                args=[i],
            )

if prompt := st.chat_input("Say something"):
    with st.chat_message("user"):
        st.write(prompt)
    st.session_state.history.append({"role": "user", "content": prompt})

    with st.chat_message("assistant"):
        with st.spinner("..."):
            response = assistant.rag(prompt)

            record = assistant.last_call
            conversation_id = db_client.save_conversation(record, prompt)
            st.session_state.conversation_id = conversation_id

            relevance, explanation = evaluate_relevance(prompt, response)
            db_client.save_feedback(conversation_id, "judge", relevance=relevance, explanation=explanation)

            st.write(response)

            st.feedback(
                "thumbs",
                key=f"feedback_{len(st.session_state.history)}",
                on_change=save_feedback,
                args=[len(st.session_state.history)],
            )
    st.session_state.history.append({"role": "assistant", "content": response})