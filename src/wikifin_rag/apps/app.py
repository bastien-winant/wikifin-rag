import streamlit as st

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
    position='top'
)
pg.run()