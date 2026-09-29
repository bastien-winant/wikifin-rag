import streamlit as st
from wikifin_rag.apps.chat.utils import reset_session_state, display_conversation_history, generate_prompt_response

with st.sidebar:
    st.title("Ask Wikifin")
    st.text("Clear answers to your money questions.")
    st.caption(
        """*This AI assistant uses information from [wikifin.be](https://www.wikifin.be) to
        answer your questions about finance, taxes, or savings in Belgium.*"""
    )


display_conversation_history()

with st.bottom:
    col1, col2 = st.columns([6, 1])

if prompt := col1.chat_input("Type in your question"):
    generate_prompt_response(prompt=prompt)


col2.button(
    'Clear chat',
    on_click=reset_session_state,
    type="primary",
    width="stretch"
)