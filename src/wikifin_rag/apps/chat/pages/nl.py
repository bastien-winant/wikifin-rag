import streamlit as st
from wikifin_rag.assistant import create_assistant
from wikifin_rag.db_client import MonitoringDBClient
from wikifin_rag.judge import evaluate_relevance
from functools import reduce
from wikifin_rag.utils import num_tokens_from_message

db_client = MonitoringDBClient()
assistant = create_assistant()


def save_feedback(exchange_id):
    st.session_state.feedback[exchange_id] = st.session_state[f"feedback_{exchange_id}"]
    db_client.save_feedback(
        exchange_id=exchange_id,
        source="user",
        score=st.session_state[f"feedback_{exchange_id}"]
    )

with st.sidebar:
    st.title("Vraag het aan Wikifin")
    st.text("Duidelijke antwoorden op je geldvragen.")
    st.caption(
        """*Deze AI-assistent gebruikt informatie van [wikifin.be](https://www.wikifin.be) om
        je vragen over financiën, belastingen of sparen in België te beantwoorden.*"""
    )


for exchange_id, messages in st.session_state.history.items():
    for message in messages:
        with st.chat_message(message["role"]):
            st.write(message["content"])

            if message["role"] == "assistant":
                feedback = st.session_state.feedback.get(exchange_id, None)
                st.session_state[f"feedback_{exchange_id}"] = feedback
                st.feedback(
                    "thumbs",
                    key=f"feedback_{exchange_id}",
                    disabled=feedback is not None,
                    on_change=save_feedback,
                    args=[exchange_id],
                )

if prompt := st.chat_input("Typ hier je vraag"):
    num_prompt_tokens = num_tokens_from_message(prompt)

    if num_prompt_tokens > st.session_state.MAX_INPUT_TOKENS:
        st.error("That message is too long.")
        st.stop()

    st.chat_message("user").write(prompt)

    with st.chat_message("assistant"):
        with st.spinner():
            messages = reduce(lambda x, y: x + y, st.session_state.history.values(), [])
            response = assistant.rag(prompt, history=messages)

            # save LLM response trace
            record = assistant.last_call

            if st.session_state.conversation_id is None:
                conversation_id = db_client.save_conversation(record)
                st.session_state.conversation_id = conversation_id

            exchange_id = db_client.save_exchange(st.session_state.conversation_id, record, prompt)
            st.session_state.exchange_id = exchange_id

            # LLM-as-a-judge
            relevance, explanation = evaluate_relevance(prompt, response)
            db_client.save_feedback(
                exchange_id=exchange_id,
                source="judge",
                relevance=relevance,
                explanation=explanation
            )

            st.write(response)
            st.feedback(
                "thumbs",
                key=f"feedback_{exchange_id}",
                on_change=save_feedback,
                args=[exchange_id],
            )
    
    st.session_state.history[exchange_id] = [
        {"role": "user", "content": prompt},
        {"role": "assistant", "content": response}
    ]
