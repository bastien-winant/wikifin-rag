import streamlit as st
import time
from wikifin_rag.assistant import create_assistant
from wikifin_rag.db_client import MonitoringDBClient
from wikifin_rag.judge import evaluate_relevance


assistant = create_assistant()

db_client = MonitoringDBClient()
db_client.init_db()


def save_feedback(index, conversation_id):
    st.session_state.history[index]["feedback"] = st.session_state[f"feedback_{conversation_id}"]
    db_client.save_feedback(conversation_id, "user", score=st.session_state[f"feedback_{conversation_id}"])


if "history" not in st.session_state:
    st.session_state.history = []


st.title("Ask Wik:blue[i]f:green[i]n")


messages = st.container(height=200)

# for i, message in enumerate(st.session_state.history):
#     with st.chat_message(message["role"]):
#         st.write(message["content"])
#         if message["role"] == "assistant":
#             conversation_id = message["id"]
#             feedback = message.get("feedback", None)
#             st.session_state[f"feedback_{conversation_id}"] = feedback
#             st.feedback(
#                 "thumbs",
#                 key=f"feedback_{conversation_id}",
#                 disabled=feedback is not None,
#                 on_change=save_feedback,
#                 args=[i, conversation_id],
#             )

if prompt := st.chat_input("Say something"):
    messages.chat_message("user").write(prompt)
    st.session_state.history.append({"role": "user", "content": prompt})

    with st.spinner():
        response = assistant.rag(prompt)

        record = assistant.last_call
        conversation_id = db_client.save_conversation(record, prompt)
        st.session_state.conversation_id = conversation_id

        # generate and save LLM-as-judge feedback
        relevance, explanation = evaluate_relevance(prompt, response)
        db_client.save_feedback(conversation_id, "judge", relevance=relevance, explanation=explanation)

        # write assistant response to the chat
        messages.chat_message("assistant").write(response)

        # listen for user feedback
        st.feedback(
            "thumbs",
            key=f"feedback_{conversation_id}",
            on_change=save_feedback,
            args=[len(st.session_state.history), conversation_id],
        )
    st.session_state.history.append({"role": "assistant", "content": response, "id": conversation_id})