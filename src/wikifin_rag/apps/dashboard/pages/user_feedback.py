import streamlit as st
from numpy.random import default_rng as rng

st.header("User Feedback")

df = rng(0).standard_normal((10, 1))

chart_tab, data_tab = st.tabs(["📈 Chart", "🗃 Data"])

# chart_tab.subheader("A tab with a chart")
chart_tab.line_chart(df)

# data_tab.subheader("A tab with the data")
data_tab.write(df)