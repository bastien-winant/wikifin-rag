import streamlit as st

pg = st.navigation(
    [
        st.Page("app_en.py", title="English", default=True),
        st.Page("app_nl.py", title="Nederlands"),
        st.Page("app_fr.py", title="Français"),
    ],
    position="hidden",
)
pg.run()
