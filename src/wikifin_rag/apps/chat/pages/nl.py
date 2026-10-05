import streamlit as st
from wikifin_rag.apps.chat.utils import reset_session_state, display_conversation_history, generate_prompt_response

with st.sidebar:
    st.title("Vraag het aan Wikifin")
    st.text("Duidelijke antwoorden op je geldvragen.")
    st.caption(
        """*Deze AI-assistent gebruikt informatie van [wikifin.be](https://www.wikifin.be) om
        je vragen over financiën, belastingen of sparen in België te beantwoorden.*"""
    )


display_conversation_history()

with st.bottom:
    col1, col2 = st.columns([6, 1])

if prompt := col1.chat_input("Typ hier je vraag"):
    generate_prompt_response(prompt=prompt, error_msg="Je bericht overschrijdt de maximale lengte. Maak het korter en probeer het opnieuw.")


col2.button(
    'Clear chat',
    on_click=reset_session_state,
    type="primary",
    width="stretch"
)