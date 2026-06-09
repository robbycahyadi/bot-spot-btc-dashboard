import streamlit as st
import pandas as pd

_PAGE_SIZES = [25, 50, 100]


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

    # ── Filters ───────────────────────────────────────────────────────────────
    col1, col2 = st.columns(2)
    with col1:
        pairs = ["All"] + sorted(df["pair"].dropna().unique().tolist())
        selected_pair = st.selectbox("Filter by pair", pairs, key="spt_tr_pair")
    with col2:
        outcome_options = ["All", "Win", "Loss", "Breakeven"]
        selected_outcome = st.selectbox("Filter by outcome", outcome_options, key="spt_tr_outcome")

    filtered = df.copy()
    if selected_pair != "All":
        filtered = filtered[filtered["pair"] == selected_pair]
    if selected_outcome == "Win":
        filtered = filtered[filtered["pnl_usd"] > 0]
    elif selected_outcome == "Loss":
        filtered = filtered[filtered["pnl_usd"] < 0]
    elif selected_outcome == "Breakeven":
        filtered = filtered[filtered["pnl_usd"] == 0]

    if filtered.empty:
        st.info("No trades match the selected filters.")
        return

    # ── Pagination ────────────────────────────────────────────────────────────
    total_rows = len(filtered)
    page_size = st.selectbox("Baris per halaman", _PAGE_SIZES, index=1, key="spt_tr_page_size")
    total_pages = max(1, -(-total_rows // page_size))

    filter_key = (selected_pair, selected_outcome, page_size)
    if st.session_state.get("spt_tr_filter_key") != filter_key:
        st.session_state["spt_tr_filter_key"] = filter_key
        st.session_state["spt_tr_page"] = 1

    page = st.session_state.get("spt_tr_page", 1)
    page = max(1, min(page, total_pages))
    st.session_state["spt_tr_page"] = page

    col_prev, col_info, col_next = st.columns([1, 4, 1])
    with col_prev:
        if st.button("← Prev", key="spt_tr_prev", disabled=page <= 1):
            st.session_state["spt_tr_page"] -= 1
            st.rerun()
    with col_info:
        st.caption(f"Halaman **{page}** dari **{total_pages}** · {total_rows} dari {len(df)} trades")
    with col_next:
        if st.button("Next →", key="spt_tr_next", disabled=page >= total_pages):
            st.session_state["spt_tr_page"] += 1
            st.rerun()

    # ── Display table (current page, formatted) ───────────────────────────────
    start = (page - 1) * page_size
    display = filtered.iloc[start : start + page_size].copy()
    display["pnl_pct"] = display["pnl_pct"].map(lambda x: f"{x:.2f}%" if pd.notna(x) else "—")
    display["pnl_usd"] = display["pnl_usd"].map(lambda x: f"${x:,.2f}" if pd.notna(x) else "—")
    display["entry_price"] = display["entry_price"].map(lambda x: f"{x:,.4f}" if pd.notna(x) else "—")
    display["exit_price"] = display["exit_price"].map(lambda x: f"{x:,.4f}" if pd.notna(x) else "—")

    st.dataframe(display, use_container_width=True)
