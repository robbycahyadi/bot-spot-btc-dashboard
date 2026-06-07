import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import plotly.express as px


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

    c5, c6, _ , __ = st.columns(4)
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

    st.dataframe(df, use_container_width=True)


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

    col1, col2, col3 = st.columns(3)
    with col1:
        side_options = ["All", "long", "short"]
        selected_side = st.selectbox("Filter by side", side_options, key="fut_side")
    with col2:
        pairs = ["All"] + sorted(df["pair"].dropna().unique().tolist())
        selected_pair = st.selectbox("Filter by pair", pairs, key="fut_pair")
    with col3:
        outcome_options = ["All", "Win", "Loss", "Breakeven"]
        selected_outcome = st.selectbox("Filter by outcome", outcome_options, key="fut_outcome")

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

    st.caption(f"Showing {len(filtered)} of {len(df)} trades")

    if filtered.empty:
        st.info("No trades match the selected filters.")
        return

    display = filtered.copy()
    for col in ["pnl_pct"]:
        display[col] = display[col].map(lambda x: f"{x:.2f}%" if pd.notna(x) else "—")
    for col in ["pnl_usd", "gross_pnl_usd", "total_fee_usd", "funding_rate_paid"]:
        display[col] = display[col].map(lambda x: f"${x:,.2f}" if pd.notna(x) else "—")
    for col in ["entry_price", "exit_price"]:
        display[col] = display[col].map(lambda x: f"{x:,.4f}" if pd.notna(x) else "—")

    st.dataframe(display, use_container_width=True)


def _render_signal_log(conn):
    st.subheader("Signal Log")
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
            ORDER BY timestamp DESC
            LIMIT 500
        """
        df = pd.read_sql(query, conn, parse_dates=["timestamp"])
    except Exception as e:
        st.error(f"Failed to load futures signal log: {e}")
        return

    if df.empty:
        st.info("No futures signal data yet.")
        return

    col1, col2 = st.columns(2)
    with col1:
        bias_opts = ["All"] + sorted(df["bias_direction"].dropna().unique().tolist())
        selected_bias = st.selectbox("Filter by bias", bias_opts, key="fut_sig_bias")
    with col2:
        temp_opts = ["All"] + sorted(df["temperature"].dropna().unique().tolist())
        selected_temp = st.selectbox("Filter by temperature", temp_opts, key="fut_sig_temp")

    filtered = df.copy()
    if selected_bias != "All":
        filtered = filtered[filtered["bias_direction"] == selected_bias]
    if selected_temp != "All":
        filtered = filtered[filtered["temperature"] == selected_temp]

    st.dataframe(filtered, use_container_width=True)

    _render_futures_reject_breakdown(filtered)


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
