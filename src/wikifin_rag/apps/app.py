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
    st.session_state.feedback_submitted = True


st.title("Ask Wik:blue[i]f:green[i]n")
container = st.container(border=True, height=330)


if new_prompt := st.chat_input("Say something"):
    st.session_state.prompt = new_prompt
    st.session_state.response = None
    st.session_state.feedback_submitted = False


prompt = st.session_state.get("prompt")

if prompt:
    container.chat_message("user").write(prompt)

    response = st.session_state.get("response")
    conversation_id = st.session_state.get("conversation_id")

    with container.chat_message("assistant"):
        if not response:
            with st.spinner("Wait for it...", show_time=True):
                # generate a response from the model
                response = assistant.rag(prompt)
                st.session_state.response = response

                # save the model trace
                record = assistant.last_call
                conversation_id = db_client.save_conversation(record, prompt)
                st.session_state.conversation_id = conversation_id

                # generate and save LLM-as-judge feedback
                relevance, explanation = evaluate_relevance(prompt, response)
                db_client.save_feedback(conversation_id, "judge", relevance=relevance, explanation=explanation)

    
        st.write(response)

        # listen for user feedback
        st.feedback(
            "thumbs",
            key=f"feedback_{conversation_id}",
            on_change=save_feedback,
            disabled=st.session_state.get("feedback_submitted", False)
        )