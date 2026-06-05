import streamlit as st
import pandas as pd
import plotly.express as px


def render(conn):
    st.header("Signal Log")

    try:
        query = """
            SELECT
                timestamp,
                pair,
                entry_triggered,
                confluence_score,
                reject_reasons
            FROM signals
            ORDER BY timestamp DESC
        """
        df = pd.read_sql(query, conn, parse_dates=["timestamp"])
    except Exception as e:
        st.error(f"Failed to load signal log: {e}")
        return

    if df.empty:
        st.info("No signal data yet.")
        return

    st.dataframe(df, use_container_width=True)
    st.divider()

    _render_reject_breakdown(df)


def _render_reject_breakdown(df):
    st.subheader("Reject Reason Breakdown")

    rejected = df[df["entry_triggered"] == False].copy()  # noqa: E712

    if rejected.empty:
        st.info("No rejected signals.")
        return

    # reject_reasons may be a list/array column or a comma-separated string
    reasons = []
    for val in rejected["reject_reasons"].dropna():
        if isinstance(val, list):
            reasons.extend(val)
        else:
            reasons.extend([r.strip() for r in str(val).split(",") if r.strip()])

    if not reasons:
        st.info("No reject reason data available.")
        return

    reason_counts = pd.Series(reasons).value_counts().reset_index()
    reason_counts.columns = ["reason", "count"]

    fig = px.pie(
        reason_counts,
        names="reason",
        values="count",
        hole=0.4,
    )
    fig.update_layout(margin=dict(l=0, r=0, t=10, b=0), height=350)
    st.plotly_chart(fig, use_container_width=True)
