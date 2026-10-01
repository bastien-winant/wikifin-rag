import streamlit as st
from wikifin_rag.apps.dashboard.queries import get_costs

st.header("Costs")

df = get_costs(
    start_date=st.session_state.from_date,
    end_date=st.session_state.to_date
)


if df.empty:
    st.warning('No data available for the given time range.')
    st.stop()


df_grouped = df.groupby(st.session_state.granularity, as_index=False)\
    [['total_cost', 'input_cost', 'output_cost']].sum()

chart_tab, data_tab = st.tabs(["📈 Chart", "🗃 Data"])

chart_tab.area_chart(
    df_grouped,
    x=st.session_state.granularity,
    y=["total_cost", "input_cost", "output_cost"],
    x_label=st.session_state.granularity.upper(),
    y_label="Costs ($)"
)

data_tab.write(df_grouped)