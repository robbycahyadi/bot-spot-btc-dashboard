import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import plotly.express as px
from datetime import date, timedelta

_PAGE_SIZES = [25, 50, 100]


def render(conn):
    st.header("Futures (bot-future-btc)")

    _render_summary_metrics(conn)
    st.divider()
    _render_equity_curve(conn)
    st.divider()
    _render_open_positions(conn)
    st.divider()
    _render_trade_history(conn)
    st.divider()
    _render_signal_log(conn)


def _render_summary_metrics(conn):
    try:
        query = """
            SELECT
                COUNT(*)                                                     AS total_trades,
                SUM(CASE WHEN pnl_usd > 0 THEN 1 ELSE 0 END)               AS winners,
                SUM(CASE WHEN pnl_usd < 0 THEN 1 ELSE 0 END)               AS losers,
                SUM(pnl_usd)                                                 AS net_pnl,
                SUM(gross_pnl_usd)                                           AS gross_pnl,
                SUM(total_fee_usd)                                           AS total_fees,
                SUM(funding_rate_paid)                                       AS total_funding,
                SUM(CASE WHEN pnl_usd > 0 THEN pnl_usd ELSE 0 END)         AS gross_profit,
                SUM(CASE WHEN pnl_usd < 0 THEN ABS(pnl_usd) ELSE 0 END)    AS gross_loss
            FROM trades
            WHERE timestamp_exit IS NOT NULL
        """
        df = pd.read_sql(query, conn)
    except Exception as e:
        st.error(f"Failed to load futures summary metrics: {e}")
        return

    if df.empty or df["total_trades"].iloc[0] == 0:
        st.info("No closed futures trades yet.")
        return

    row = df.iloc[0]
    total = int(row["total_trades"])
    winners = int(row["winners"] or 0)
    net_pnl = float(row["net_pnl"] or 0)
    gross_profit = float(row["gross_profit"] or 0)
    gross_loss = float(row["gross_loss"] or 0)
    total_fees = float(row["total_fees"] or 0)
    total_funding = float(row["total_funding"] or 0)

    winrate = (winners / total * 100) if total > 0 else 0
    profit_factor = (gross_profit / gross_loss) if gross_loss > 0 else float("inf")
    pf_display = f"{profit_factor:.2f}" if profit_factor != float("inf") else "∞"

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Total Trades", total)
    c2.metric("Win Rate", f"{winrate:.1f}%")
    c3.metric("Profit Factor", pf_display)
    c4.metric("Net PnL (after fees)", f"${net_pnl:,.2f}", delta=f"${net_pnl:,.2f}")

    c5, c6, _, __ = st.columns(4)
    c5.metric("Total Fees", f"${total_fees:,.2f}")
    c6.metric("Total Funding Paid", f"${total_funding:,.2f}")


def _render_equity_curve(conn):
    st.subheader("Equity Curve")
    try:
        query = """
            SELECT timestamp_exit, pnl_usd, side
            FROM trades
            WHERE timestamp_exit IS NOT NULL
            ORDER BY timestamp_exit ASC
        """
        df = pd.read_sql(query, conn, parse_dates=["timestamp_exit"])
    except Exception as e:
        st.error(f"Failed to load futures equity curve: {e}")
        return

    if df.empty:
        st.info("No data yet.")
        return

    df["cumulative_pnl"] = df["pnl_usd"].cumsum()

    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=df["timestamp_exit"],
        y=df["cumulative_pnl"],
        mode="lines",
        name="Cumulative Net PnL",
        line=dict(color="#4895ef", width=2),
        fill="tozeroy",
        fillcolor="rgba(72,149,239,0.1)",
    ))
    fig.update_layout(
        xaxis_title="Date",
        yaxis_title="Cumulative Net PnL (USD)",
        margin=dict(l=0, r=0, t=10, b=0),
        height=300,
    )
    st.plotly_chart(fig, use_container_width=True)


def _render_open_positions(conn):
    st.subheader("Open Positions")
    try:
        query = """
            SELECT
                timestamp_entry,
                pair,
                side,
                leverage,
                entry_price,
                liquidation_price,
                sl_price,
                tp1_price,
                position_size_usd,
                margin_used_usd
            FROM trades
            WHERE timestamp_exit IS NULL
            ORDER BY timestamp_entry DESC
        """
        df = pd.read_sql(query, conn, parse_dates=["timestamp_entry"])
    except Exception as e:
        st.error(f"Failed to load open positions: {e}")
        return

    if df.empty:
        st.info("No open futures positions.")
        return

    # ── Pagination ────────────────────────────────────────────────────────────
    total_rows = len(df)
    page_size = st.selectbox("Baris per halaman", _PAGE_SIZES, index=1, key="fut_pos_page_size")
    total_pages = max(1, -(-total_rows // page_size))

    if st.session_state.get("fut_pos_page_size_prev") != page_size:
        st.session_state["fut_pos_page_size_prev"] = page_size
        st.session_state["fut_pos_page"] = 1

    page = st.session_state.get("fut_pos_page", 1)
    page = max(1, min(page, total_pages))
    st.session_state["fut_pos_page"] = page

    col_prev, col_info, col_next = st.columns([1, 4, 1])
    with col_prev:
        if st.button("← Prev", key="fut_pos_prev", disabled=page <= 1):
            st.session_state["fut_pos_page"] -= 1
            st.rerun()
    with col_info:
        st.caption(f"Halaman **{page}** dari **{total_pages}** · {total_rows} posisi")
    with col_next:
        if st.button("Next →", key="fut_pos_next", disabled=page >= total_pages):
            st.session_state["fut_pos_page"] += 1
            st.rerun()

    start = (page - 1) * page_size
    st.dataframe(df.iloc[start : start + page_size], use_container_width=True)


def _render_trade_history(conn):
    st.subheader("Trade History")
    try:
        query = """
            SELECT
                timestamp_entry,
                pair,
                side,
                leverage,
                entry_price,
                exit_price,
                pnl_pct,
                pnl_usd,
                gross_pnl_usd,
                total_fee_usd,
                funding_rate_paid,
                exit_reason,
                rr_actual,
                holding_duration_h
            FROM trades
            WHERE timestamp_exit IS NOT NULL
            ORDER BY timestamp_entry DESC
        """
        df = pd.read_sql(query, conn, parse_dates=["timestamp_entry"])
    except Exception as e:
        st.error(f"Failed to load futures trade history: {e}")
        return

    if df.empty:
        st.info("No closed futures trades yet.")
        return

    # ── Filters ───────────────────────────────────────────────────────────────
    col1, col2, col3 = st.columns(3)
    with col1:
        selected_side = st.selectbox("Filter by side", ["All", "long", "short"], key="fut_side")
    with col2:
        pairs = ["All"] + sorted(df["pair"].dropna().unique().tolist())
        selected_pair = st.selectbox("Filter by pair", pairs, key="fut_pair")
    with col3:
        selected_outcome = st.selectbox(
            "Filter by outcome", ["All", "Win", "Loss", "Breakeven"], key="fut_outcome"
        )

    filtered = df.copy()
    if selected_side != "All":
        filtered = filtered[filtered["side"] == selected_side]
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
    page_size = st.selectbox("Baris per halaman", _PAGE_SIZES, index=1, key="fut_tr_page_size")
    total_pages = max(1, -(-total_rows // page_size))

    filter_key = (selected_side, selected_pair, selected_outcome, page_size)
    if st.session_state.get("fut_tr_filter_key") != filter_key:
        st.session_state["fut_tr_filter_key"] = filter_key
        st.session_state["fut_tr_page"] = 1

    page = st.session_state.get("fut_tr_page", 1)
    page = max(1, min(page, total_pages))
    st.session_state["fut_tr_page"] = page

    col_prev, col_info, col_next = st.columns([1, 4, 1])
    with col_prev:
        if st.button("← Prev", key="fut_tr_prev", disabled=page <= 1):
            st.session_state["fut_tr_page"] -= 1
            st.rerun()
    with col_info:
        st.caption(f"Halaman **{page}** dari **{total_pages}** · {total_rows} dari {len(df)} trades")
    with col_next:
        if st.button("Next →", key="fut_tr_next", disabled=page >= total_pages):
            st.session_state["fut_tr_page"] += 1
            st.rerun()

    # ── Display table (current page, formatted) ───────────────────────────────
    start = (page - 1) * page_size
    display = filtered.iloc[start : start + page_size].copy()
    for col in ["pnl_pct"]:
        display[col] = display[col].map(lambda x: f"{x:.2f}%" if pd.notna(x) else "—")
    for col in ["pnl_usd", "gross_pnl_usd", "total_fee_usd", "funding_rate_paid"]:
        display[col] = display[col].map(lambda x: f"${x:,.2f}" if pd.notna(x) else "—")
    for col in ["entry_price", "exit_price"]:
        display[col] = display[col].map(lambda x: f"{x:,.4f}" if pd.notna(x) else "—")

    st.dataframe(display, use_container_width=True)


def _render_signal_log(conn):
    st.subheader("Signal Log")

    today = date.today()
    default_from = today - timedelta(days=7)

    col1, col2, col3, col4 = st.columns([2, 2, 2, 2])
    with col1:
        date_from = st.date_input("Dari", value=default_from, key="fut_sig_date_from")
    with col2:
        date_to = st.date_input("Sampai", value=today, key="fut_sig_date_to")
    with col3:
        pair_filter = st.selectbox("Pair", ["All", "BTC/USDT", "ETH/USDT"], key="fut_sig_pair")
    with col4:
        entry_filter = st.selectbox(
            "Entry Triggered",
            ["All", "Entry only", "Rejected only"],
            key="fut_sig_entry",
        )

    bias_filter = st.selectbox(
        "Bias Direction", ["All", "LONG", "SHORT", "NEUTRAL"], key="fut_sig_bias"
    )

    try:
        query = """
            SELECT
                timestamp,
                pair,
                timeframe,
                signal_type,
                entry_triggered,
                bias_direction,
                temperature,
                confluence_score,
                funding_rate,
                reject_reasons
            FROM signals
            WHERE timestamp::date BETWEEN %(date_from)s AND %(date_to)s
            ORDER BY timestamp DESC
        """
        df = pd.read_sql(
            query,
            conn,
            params={"date_from": date_from, "date_to": date_to},
            parse_dates=["timestamp"],
        )
    except Exception as e:
        st.error(f"Failed to load futures signal log: {e}")
        return

    if df.empty:
        st.info("No futures signal data for the selected date range.")
        return

    if pair_filter != "All":
        df = df[df["pair"] == pair_filter]
    if entry_filter == "Entry only":
        df = df[df["entry_triggered"] == True]   # noqa: E712
    elif entry_filter == "Rejected only":
        df = df[df["entry_triggered"] == False]  # noqa: E712
    if bias_filter != "All":
        df = df[df["bias_direction"] == bias_filter]

    if df.empty:
        st.info("No signals match the current filters.")
        return

    # ── Download CSV (all filtered rows) ──────────────────────────────────────
    pair_slug = pair_filter.replace("/", "-").lower()
    csv_filename = f"futures_signals_{pair_slug}_{date_from}_{date_to}.csv"
    st.download_button(
        label="Download CSV",
        data=df.to_csv(index=False).encode("utf-8"),
        file_name=csv_filename,
        mime="text/csv",
    )

    # ── Pagination ────────────────────────────────────────────────────────────
    total_rows = len(df)
    page_size = st.selectbox(
        "Baris per halaman", _PAGE_SIZES, index=1, key="fut_sig_page_size"
    )
    total_pages = max(1, -(-total_rows // page_size))

    filter_key = (str(date_from), str(date_to), pair_filter, entry_filter, bias_filter, page_size)
    if st.session_state.get("fut_sig_filter_key") != filter_key:
        st.session_state["fut_sig_filter_key"] = filter_key
        st.session_state["fut_sig_page"] = 1

    page = st.session_state.get("fut_sig_page", 1)
    page = max(1, min(page, total_pages))
    st.session_state["fut_sig_page"] = page

    col_prev, col_info, col_next = st.columns([1, 4, 1])
    with col_prev:
        if st.button("← Prev", key="fut_sig_prev", disabled=page <= 1):
            st.session_state["fut_sig_page"] -= 1
            st.rerun()
    with col_info:
        st.caption(f"Halaman **{page}** dari **{total_pages}** · {total_rows} sinyal total")
    with col_next:
        if st.button("Next →", key="fut_sig_next", disabled=page >= total_pages):
            st.session_state["fut_sig_page"] += 1
            st.rerun()

    # ── Display table (current page only) ────────────────────────────────────
    start = (page - 1) * page_size
    page_df = df.iloc[start : start + page_size].copy()
    page_df["reject_reasons"] = page_df["reject_reasons"].apply(_truncate)
    st.dataframe(page_df, use_container_width=True)

    # Reject breakdown uses full filtered df, not just current page
    _render_futures_reject_breakdown(df)


def _truncate(val, max_len=80):
    if val is None or (isinstance(val, float) and pd.isna(val)):
        return ""
    text = str(val)
    return text if len(text) <= max_len else text[:max_len] + "…"


def _render_futures_reject_breakdown(df):
    st.subheader("Reject Reason Breakdown")

    rejected = df[df["entry_triggered"] == False].copy()  # noqa: E712

    if rejected.empty:
        st.info("No rejected signals in current filter.")
        return

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
