import streamlit as st
from wikifin_rag.apps.dashboard.queries import get_tokens

st.header("Token Usage")

df = get_tokens(
    start_date=st.session_state.from_date,
    end_date=st.session_state.to_date
)


if df.empty:
    st.warning('No data available for the given time range.')
    st.stop()


df_grouped = df.groupby(st.session_state.granularity, as_index=False)\
    [["total_tokens", "input_tokens", "output_tokens"]].sum()

chart_tab, data_tab = st.tabs(["📈 Chart", "🗃 Data"])

chart_tab.line_chart(
    df_grouped,
    x=st.session_state.granularity,
    y=["total_tokens", "input_tokens", "output_tokens"],
    x_label=st.session_state.granularity.upper(),
    y_label="Tokens"
)

data_tab.write(df_grouped)