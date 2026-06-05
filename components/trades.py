import streamlit as st
import pandas as pd


def render(conn):
    st.header("Trade History")

    try:
        query = """
            SELECT
                timestamp_entry,
                pair,
                entry_price,
                exit_price,
                pnl_pct,
                pnl_usd,
                exit_reason,
                holding_duration_h
            FROM trades
            WHERE timestamp_exit IS NOT NULL
            ORDER BY timestamp_entry DESC
        """
        df = pd.read_sql(query, conn, parse_dates=["timestamp_entry"])
    except Exception as e:
        st.error(f"Failed to load trade history: {e}")
        return

    if df.empty:
        st.info("No closed trades yet.")
        return

    # Filters
    col1, col2 = st.columns(2)
    with col1:
        pairs = ["All"] + sorted(df["pair"].dropna().unique().tolist())
        selected_pair = st.selectbox("Filter by pair", pairs)
    with col2:
        outcome_options = ["All", "Win", "Loss", "Breakeven"]
        selected_outcome = st.selectbox("Filter by outcome", outcome_options)

    filtered = df.copy()
    if selected_pair != "All":
        filtered = filtered[filtered["pair"] == selected_pair]
    if selected_outcome == "Win":
        filtered = filtered[filtered["pnl_usd"] > 0]
    elif selected_outcome == "Loss":
        filtered = filtered[filtered["pnl_usd"] < 0]
    elif selected_outcome == "Breakeven":
        filtered = filtered[filtered["pnl_usd"] == 0]

    st.caption(f"Showing {len(filtered)} of {len(df)} trades")

    if filtered.empty:
        st.info("No trades match the selected filters.")
        return

    # Format display
    display = filtered.copy()
    display["pnl_pct"] = display["pnl_pct"].map(lambda x: f"{x:.2f}%" if pd.notna(x) else "—")
    display["pnl_usd"] = display["pnl_usd"].map(lambda x: f"${x:,.2f}" if pd.notna(x) else "—")
    display["entry_price"] = display["entry_price"].map(lambda x: f"{x:,.4f}" if pd.notna(x) else "—")
    display["exit_price"] = display["exit_price"].map(lambda x: f"{x:,.4f}" if pd.notna(x) else "—")

    st.dataframe(display, use_container_width=True)
