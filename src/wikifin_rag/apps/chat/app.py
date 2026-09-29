import streamlit as st

st.session_state.MAX_INPUT_TOKENS = 2000

if "history" not in st.session_state:
    st.session_state.history = {}

if "feedback" not in st.session_state:
    st.session_state.feedback = {}

if "conversation_id" not in st.session_state:
    st.session_state.conversation_id = None

pg = st.navigation(
    pages=[
        st.Page(
            "pages/en.py",
            title="🇬🇧 EN",
            url_path="en"
        ),
        st.Page(
            "pages/fr.py",
            title="🇫🇷 FR",
            url_path="fr"
        ),
        st.Page(
            "pages/nl.py",
            title="🇳🇱 NL",
            url_path="nl"
        ),
    ],
)
st.set_page_config(page_title="Wikifin AI")
pg.run()