import streamlit as st
import time
from wikifin_rag.assistant import create_assistant
from wikifin_rag.db_client import MonitoringDBClient
from wikifin_rag.judge import evaluate_relevance

db_client = MonitoringDBClient()
assistant = create_assistant()


def save_feedback(index):
    conversation_id = st.session_state.conversation_id
    st.session_state.history[index]["feedback"] = st.session_state[f"feedback_{conversation_id}"]
    db_client.save_feedback(
        conversation_id=conversation_id,
        source="user",
        score=st.session_state[f"feedback_{conversation_id}"]
    )


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
    st.chat_message("user").write(prompt)
    st.session_state.history.append({"role": "user", "content": prompt})
    
    with st.chat_message("assistant"):
        with st.spinner():
            response = assistant.rag(prompt)

            # save LLM response trace
            record = assistant.last_call
            conversation_id = db_client.save_conversation(record, prompt)
            st.session_state.conversation_id = conversation_id

            # LLM-as-a-judge
            relevance, explanation = evaluate_relevance(prompt, response)
            db_client.save_feedback(
                conversation_id=conversation_id,
                source="judge",
                relevance=relevance,
                explanation=explanation
            )
            
            st.write(response)
            st.feedback(
                "thumbs",
                key=f"feedback_{conversation_id}",
                on_change=save_feedback,
                args=[len(st.session_state.history)],
            )
    st.session_state.history.append({"role": "assistant", "content": response})