import streamlit as st
import pandas as pd
import plotly.graph_objects as go


def render(conn_spot, conn_futures):
    st.header("Portfolio — Spot + Futures")

    _render_combined_metrics(conn_spot, conn_futures)
    st.divider()
    _render_equity_overlay(conn_spot, conn_futures)
    st.divider()
    _render_bot_summary_table(conn_spot, conn_futures)


def _fetch_closed_pnl(conn, label: str):
    """Return DataFrame with columns [timestamp_exit, pnl_usd] for closed trades."""
    if conn is None:
        return pd.DataFrame(columns=["timestamp_exit", "pnl_usd"])
    try:
        query = """
            SELECT timestamp_exit, pnl_usd
            FROM trades
            WHERE timestamp_exit IS NOT NULL
            ORDER BY timestamp_exit ASC
        """
        return pd.read_sql(query, conn, parse_dates=["timestamp_exit"])
    except Exception as e:
        st.warning(f"Could not fetch PnL for {label}: {e}")
        return pd.DataFrame(columns=["timestamp_exit", "pnl_usd"])


def _bot_summary_row(conn, label: str) -> dict:
    """Return summary stats dict for one bot."""
    if conn is None:
        return {"bot": label, "trades": 0, "winners": 0, "winrate": "—", "net_pnl": "—"}
    try:
        query = """
            SELECT
                COUNT(*)                                                    AS total_trades,
                SUM(CASE WHEN pnl_usd > 0 THEN 1 ELSE 0 END)              AS winners,
                SUM(pnl_usd)                                                AS net_pnl
            FROM trades
            WHERE timestamp_exit IS NOT NULL
        """
        df = pd.read_sql(query, conn)
    except Exception as e:
        st.warning(f"Could not fetch summary for {label}: {e}")
        return {"bot": label, "trades": 0, "winners": 0, "winrate": "—", "net_pnl": "—"}

    if df.empty or df["total_trades"].iloc[0] == 0:
        return {"bot": label, "trades": 0, "winners": 0, "winrate": "0.0%", "net_pnl": "$0.00"}

    row = df.iloc[0]
    total = int(row["total_trades"])
    winners = int(row["winners"] or 0)
    net_pnl = float(row["net_pnl"] or 0)
    winrate = (winners / total * 100) if total > 0 else 0

    return {
        "bot": label,
        "trades": total,
        "winners": winners,
        "winrate": f"{winrate:.1f}%",
        "net_pnl": f"${net_pnl:,.2f}",
        "_net_pnl_raw": net_pnl,
    }


def _render_combined_metrics(conn_spot, conn_futures):
    spot = _bot_summary_row(conn_spot, "Spot")
    fut = _bot_summary_row(conn_futures, "Futures")

    spot_pnl = spot.get("_net_pnl_raw", 0) or 0
    fut_pnl = fut.get("_net_pnl_raw", 0) or 0
    combined_pnl = spot_pnl + fut_pnl

    c1, c2, c3 = st.columns(3)
    c1.metric("Spot Net PnL", f"${spot_pnl:,.2f}", delta=f"${spot_pnl:,.2f}")
    c2.metric("Futures Net PnL", f"${fut_pnl:,.2f}", delta=f"${fut_pnl:,.2f}")
    c3.metric("Combined Net PnL", f"${combined_pnl:,.2f}", delta=f"${combined_pnl:,.2f}")


def _render_equity_overlay(conn_spot, conn_futures):
    st.subheader("Equity Curve Overlay")

    df_spot = _fetch_closed_pnl(conn_spot, "Spot")
    df_fut = _fetch_closed_pnl(conn_futures, "Futures")

    if df_spot.empty and df_fut.empty:
        st.info("No closed trade data available for either bot.")
        return

    fig = go.Figure()

    if not df_spot.empty:
        df_spot["cumulative_pnl"] = df_spot["pnl_usd"].cumsum()
        fig.add_trace(go.Scatter(
            x=df_spot["timestamp_exit"],
            y=df_spot["cumulative_pnl"],
            mode="lines",
            name="Spot",
            line=dict(color="#00b4d8", width=2),
        ))

    if not df_fut.empty:
        df_fut["cumulative_pnl"] = df_fut["pnl_usd"].cumsum()
        fig.add_trace(go.Scatter(
            x=df_fut["timestamp_exit"],
            y=df_fut["cumulative_pnl"],
            mode="lines",
            name="Futures",
            line=dict(color="#4895ef", width=2),
        ))

    if not df_spot.empty and not df_fut.empty:
        combined = (
            pd.concat([
                df_spot[["timestamp_exit", "pnl_usd"]],
                df_fut[["timestamp_exit", "pnl_usd"]],
            ])
            .sort_values("timestamp_exit")
            .reset_index(drop=True)
        )
        combined["cumulative_pnl"] = combined["pnl_usd"].cumsum()
        fig.add_trace(go.Scatter(
            x=combined["timestamp_exit"],
            y=combined["cumulative_pnl"],
            mode="lines",
            name="Combined",
            line=dict(color="#f77f00", width=2, dash="dot"),
        ))

    fig.update_layout(
        xaxis_title="Date",
        yaxis_title="Cumulative Net PnL (USD)",
        margin=dict(l=0, r=0, t=10, b=0),
        height=350,
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
    )
    st.plotly_chart(fig, use_container_width=True)


def _render_bot_summary_table(conn_spot, conn_futures):
    st.subheader("Per-Bot Summary")

    spot = _bot_summary_row(conn_spot, "Spot (bot-spot-btc)")
    fut = _bot_summary_row(conn_futures, "Futures (bot-future-btc)")

    rows = []
    for r in [spot, fut]:
        rows.append({
            "Bot": r["bot"],
            "Closed Trades": r["trades"],
            "Winners": r["winners"],
            "Win Rate": r["winrate"],
            "Net PnL": r["net_pnl"],
        })

    st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True)
