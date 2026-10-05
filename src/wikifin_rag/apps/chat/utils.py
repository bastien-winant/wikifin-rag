import streamlit as st
from wikifin_rag.assistant import create_assistant
from wikifin_rag.judge import evaluate_relevance
from functools import reduce
from wikifin_rag.utils import num_tokens_from_message
from wikifin_rag.apps.chat.queries import save_conversation, save_exchange, save_feedback


def get_assistant():
    return create_assistant()


def reset_session_state():
    st.session_state.history = {}
    st.session_state.feedback = {}
    st.session_state.conversation_id = None


def save_user_feedback(exchange_id):
    st.session_state.feedback[exchange_id] = st.session_state[f"feedback_{exchange_id}"]
    save_feedback(
        exchange_id=exchange_id,
        source="user",
        score=st.session_state[f"feedback_{exchange_id}"]
    )


def display_conversation_history():
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
                        on_change=save_user_feedback,
                        args=[exchange_id],
                    )


def generate_prompt_response(prompt, error_msg="Your message exceeds the maximum length. Please shorten it and try again."):
    try:
        num_prompt_tokens = num_tokens_from_message(prompt)

        if num_prompt_tokens > st.session_state.MAX_INPUT_TOKENS:
            st.error(error_msg)
            st.stop()

        st.chat_message("user").write(prompt)

        with st.spinner():
            assistant = get_assistant()
            messages = reduce(lambda x, y: x + y, st.session_state.history.values(), [])
            response = assistant.rag(prompt, history=messages)

            # save LLM response trace
            record = assistant.last_call

            if st.session_state.conversation_id is None:
                conversation_id = save_conversation(record)
                st.session_state.conversation_id = conversation_id

            exchange_id = save_exchange(st.session_state.conversation_id, record, prompt)
            st.session_state.exchange_id = exchange_id

            # LLM-as-a-judge
            relevance, explanation = evaluate_relevance(prompt, response)
            save_feedback(
                exchange_id=exchange_id,
                source="judge",
                relevance=relevance,
                explanation=explanation
            )
    except:
        st.error("There was an error generating a response. Please try again later.")
        st.stop()
    finally:
        with st.chat_message("assistant"):
            st.write(response)
            st.feedback(
                "thumbs",
                key=f"feedback_{exchange_id}",
                on_change=save_user_feedback,
                args=[exchange_id],
            )

        st.session_state.history[exchange_id] = [
            {"role": "user", "content": prompt},
            {"role": "assistant", "content": response}
        ]
