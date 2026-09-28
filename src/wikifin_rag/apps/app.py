import streamlit as st

if "history" not in st.session_state:
    st.session_state.history = {}

if "feedback" not in st.session_state:
    st.session_state.feedback = {}

pg = st.navigation(
    pages=[
        st.Page(
            "app_en.py",
            title="🇬🇧 EN",
            url_path="en"
        ),
        st.Page(
            "app_fr.py",
            title="🇫🇷 FR",
            url_path="fr"
        ),
        st.Page(
            "app_nl.py",
            title="🇳🇱 NL",
            url_path="nl"
        ),
    ],
    # position='top'
)
pg.run()