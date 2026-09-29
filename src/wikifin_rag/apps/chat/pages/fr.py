import streamlit as st
from wikifin_rag.apps.chat.utils import reset_session_state, display_conversation_history, generate_prompt_response

with st.sidebar:
    st.title("Demandez à Wikifin")
    st.text("Des réponses claires à vos questions d'argent.")
    st.caption(
        """*Cet assistant IA utilise les informations de [wikifin.be](https://www.wikifin.be) pour
        répondre à vos questions sur la finance, les impôts ou l'épargne en Belgique.*"""
    )


display_conversation_history()

with st.bottom:
    col1, col2 = st.columns([6, 1])

if prompt := col1.chat_input("Tapez votre question ici"):
    generate_prompt_response(prompt=prompt)


col2.button(
    'Clear chat',
    on_click=reset_session_state,
    type="primary",
    width="stretch"
)