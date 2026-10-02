import streamlit as st
from wikifin_rag.apps.dashboard.queries import get_tokens

try:
    df = get_tokens(
        start_date=st.session_state.from_date,
        end_date=st.session_state.to_date
    )
except Exception as e:
    print(e)
    st.error("There was an error retrieving the data. Please try again later.")
    st.stop()

with st.container(gap="medium"):
    st.header("Token Usage")

    if df.empty:
        st.warning('No data available for the given time range.')
        st.stop()


    total_tokens = df.total_tokens.sum()
    total_input_tokens = df.input_tokens.sum()
    total_output_tokens = df.output_tokens.sum()

    col1, col2, col3 = st.columns(3)

    with col1:
        st.badge("Input Tokens", color="blue")
        st.text(total_input_tokens)

    with col2:
        st.badge("Output Tokens", color="yellow")
        st.text(total_output_tokens)

    with col3:
        st.badge("Total Tokens", color="green")
        st.text(total_tokens)


    df_grouped = df.groupby(st.session_state.granularity, as_index=False)\
        [["total_tokens", "input_tokens", "output_tokens"]].sum()

    chart_tab, data_tab = st.tabs(["📈 Chart", "🗃 Data"])

    chart_tab.line_chart(
        df_grouped,
        x=st.session_state.granularity,
        y=["total_tokens", "input_tokens", "output_tokens"],
        x_label=st.session_state.granularity.upper(),
        y_label="Tokens",
        color=["green", "blue", "yellow"]
    )

    data_tab.write(df_grouped)