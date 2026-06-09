import streamlit as st
import pandas as pd
import plotly.graph_objects as go

_PAGE_SIZES = [25, 50, 100]


def render(conn):
    st.header("Overview")

    _render_summary_metrics(conn)
    st.divider()
    _render_equity_curve(conn)
    st.divider()
    _render_open_positions(conn)


def _render_summary_metrics(conn):
    try:
        query = """
            SELECT
                COUNT(*) AS total_trades,
                SUM(CASE WHEN pnl_usd > 0 THEN 1 ELSE 0 END) AS winners,
                SUM(CASE WHEN pnl_usd < 0 THEN 1 ELSE 0 END) AS losers,
                SUM(pnl_usd) AS total_pnl,
                SUM(CASE WHEN pnl_usd > 0 THEN pnl_usd ELSE 0 END) AS gross_profit,
                SUM(CASE WHEN pnl_usd < 0 THEN ABS(pnl_usd) ELSE 0 END) AS gross_loss
            FROM trades
            WHERE timestamp_exit IS NOT NULL
        """
        df = pd.read_sql(query, conn)
    except Exception as e:
        st.error(f"Failed to load summary metrics: {e}")
        return

    if df.empty or df["total_trades"].iloc[0] == 0:
        st.info("No closed trades yet.")
        return

    row = df.iloc[0]
    total = int(row["total_trades"])
    winners = int(row["winners"] or 0)
    gross_profit = float(row["gross_profit"] or 0)
    gross_loss = float(row["gross_loss"] or 0)
    total_pnl = float(row["total_pnl"] or 0)

    winrate = (winners / total * 100) if total > 0 else 0
    profit_factor = (gross_profit / gross_loss) if gross_loss > 0 else float("inf")
    pf_display = f"{profit_factor:.2f}" if profit_factor != float("inf") else "∞"

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Total Trades", total)
    c2.metric("Win Rate", f"{winrate:.1f}%")
    c3.metric("Profit Factor", pf_display)
    c4.metric("Total PnL", f"${total_pnl:,.2f}", delta=f"${total_pnl:,.2f}")


def _render_equity_curve(conn):
    st.subheader("Equity Curve")
    try:
        query = """
            SELECT timestamp_exit, pnl_usd
            FROM trades
            WHERE timestamp_exit IS NOT NULL
            ORDER BY timestamp_exit ASC
        """
        df = pd.read_sql(query, conn, parse_dates=["timestamp_exit"])
    except Exception as e:
        st.error(f"Failed to load equity curve data: {e}")
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
        name="Cumulative PnL",
        line=dict(color="#00b4d8", width=2),
        fill="tozeroy",
        fillcolor="rgba(0,180,216,0.1)",
    ))
    fig.update_layout(
        xaxis_title="Date",
        yaxis_title="Cumulative PnL (USD)",
        margin=dict(l=0, r=0, t=10, b=0),
        height=300,
    )
    st.plotly_chart(fig, use_container_width=True)


def _render_open_positions(conn):
    st.subheader("Open Positions")
    try:
        query = """
            SELECT timestamp_entry, pair, entry_price, position_size
            FROM trades
            WHERE timestamp_exit IS NULL
            ORDER BY timestamp_entry DESC
        """
        df = pd.read_sql(query, conn, parse_dates=["timestamp_entry"])
    except Exception as e:
        st.error(f"Failed to load open positions: {e}")
        return

    if df.empty:
        st.info("No open positions.")
        return

    # ── Pagination ────────────────────────────────────────────────────────────
    total_rows = len(df)
    page_size = st.selectbox("Baris per halaman", _PAGE_SIZES, index=1, key="spt_pos_page_size")
    total_pages = max(1, -(-total_rows // page_size))

    if st.session_state.get("spt_pos_page_size_prev") != page_size:
        st.session_state["spt_pos_page_size_prev"] = page_size
        st.session_state["spt_pos_page"] = 1

    page = st.session_state.get("spt_pos_page", 1)
    page = max(1, min(page, total_pages))
    st.session_state["spt_pos_page"] = page

    col_prev, col_info, col_next = st.columns([1, 4, 1])
    with col_prev:
        if st.button("← Prev", key="spt_pos_prev", disabled=page <= 1):
            st.session_state["spt_pos_page"] -= 1
            st.rerun()
    with col_info:
        st.caption(f"Halaman **{page}** dari **{total_pages}** · {total_rows} posisi")
    with col_next:
        if st.button("Next →", key="spt_pos_next", disabled=page >= total_pages):
            st.session_state["spt_pos_page"] += 1
            st.rerun()

    start = (page - 1) * page_size
    st.dataframe(df.iloc[start : start + page_size], use_container_width=True)
