import streamlit as st
from wikifin_rag.assistant import create_assistant
from wikifin_rag.db_client import MonitoringDBClient
from wikifin_rag.judge import evaluate_relevance
from functools import reduce

db_client = MonitoringDBClient()
assistant = create_assistant()


def save_feedback(conversation_id):
    st.session_state.feedback[conversation_id] = st.session_state[f"feedback_{conversation_id}"]
    db_client.save_feedback(
        conversation_id=conversation_id,
        source="user",
        score=st.session_state[f"feedback_{conversation_id}"]
    )
    

with st.sidebar:
    st.title("Ask Wikifin")
    st.text("Clear answers to your money questions.")
    st.caption(
        """*This AI assistant uses information from [wikifin.be](https://www.wikifin.be) to
        answer your questions about finance, taxes, or savings in Belgium.*"""
    )


for conversation_id, messages in st.session_state.history.items():
    for message in messages:
        with st.chat_message(message["role"]):
            st.write(message["content"])

            if message["role"] == "assistant":
                feedback = st.session_state.feedback.get(conversation_id, None)
                st.session_state[f"feedback_{conversation_id}"] = feedback
                st.feedback(
                    "thumbs",
                    key=f"feedback_{conversation_id}",
                    disabled=feedback is not None,
                    on_change=save_feedback,
                    args=[conversation_id],
                )

if prompt := st.chat_input("Type in your question"):
    if len(prompt) > st.session_state.MAX_INPUT_LEN:
            st.error("That message is too long.")
            st.stop()
            
    st.chat_message("user").write(prompt)

    with st.chat_message("assistant"):
        with st.spinner():
            messages = reduce(lambda x, y: x + y, st.session_state.history.values(), [])
            response = assistant.rag(prompt, history=messages)

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
                args=[conversation_id],
            )
    
    st.session_state.history[conversation_id] = [
        {"role": "user", "content": prompt},
        {"role": "assistant", "content": response}
    ]