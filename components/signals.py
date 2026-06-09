import streamlit as st
import pandas as pd
import plotly.express as px
from datetime import date, timedelta

_PAGE_SIZES = [25, 50, 100]


def render(conn):
    st.header("Signal Log")

    # ── Filters ───────────────────────────────────────────────────────────────
    today = date.today()
    default_from = today - timedelta(days=7)

    col1, col2, col3, col4 = st.columns([2, 2, 2, 2])
    with col1:
        date_from = st.date_input("Dari", value=default_from, key="sig_date_from")
    with col2:
        date_to = st.date_input("Sampai", value=today, key="sig_date_to")
    with col3:
        pair_filter = st.selectbox(
            "Pair", ["All", "BTC/USDT", "ETH/USDT"], key="sig_pair"
        )
    with col4:
        entry_filter = st.selectbox(
            "Entry Triggered",
            ["All", "Entry only", "Rejected only"],
            key="sig_entry",
        )

    # ── Fetch ─────────────────────────────────────────────────────────────────
    try:
        query = """
            SELECT
                timestamp,
                pair,
                entry_triggered,
                confluence_score,
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
        st.error(f"Failed to load signal log: {e}")
        return

    if df.empty:
        st.info("No signal data for the selected date range.")
        return

    # ── Apply in-memory filters ────────────────────────────────────────────────
    if pair_filter != "All":
        df = df[df["pair"] == pair_filter]
    if entry_filter == "Entry only":
        df = df[df["entry_triggered"] == True]   # noqa: E712
    elif entry_filter == "Rejected only":
        df = df[df["entry_triggered"] == False]  # noqa: E712

    if df.empty:
        st.info("No signals match the current filters.")
        return

    # ── Download CSV (all filtered rows) ──────────────────────────────────────
    pair_slug = pair_filter.replace("/", "-").lower()
    csv_filename = f"signals_{pair_slug}_{date_from}_{date_to}.csv"
    st.download_button(
        label="Download CSV",
        data=df.to_csv(index=False).encode("utf-8"),
        file_name=csv_filename,
        mime="text/csv",
    )

    # ── Pagination ────────────────────────────────────────────────────────────
    total_rows = len(df)
    page_size = st.selectbox(
        "Baris per halaman", _PAGE_SIZES, index=1, key="sig_page_size"
    )
    total_pages = max(1, -(-total_rows // page_size))

    filter_key = (str(date_from), str(date_to), pair_filter, entry_filter, page_size)
    if st.session_state.get("sig_filter_key") != filter_key:
        st.session_state["sig_filter_key"] = filter_key
        st.session_state["sig_page"] = 1

    page = st.session_state.get("sig_page", 1)
    page = max(1, min(page, total_pages))
    st.session_state["sig_page"] = page

    col_prev, col_info, col_next = st.columns([1, 4, 1])
    with col_prev:
        if st.button("← Prev", key="sig_prev", disabled=page <= 1):
            st.session_state["sig_page"] -= 1
            st.rerun()
    with col_info:
        st.caption(f"Halaman **{page}** dari **{total_pages}** · {total_rows} sinyal total")
    with col_next:
        if st.button("Next →", key="sig_next", disabled=page >= total_pages):
            st.session_state["sig_page"] += 1
            st.rerun()

    # ── Display table (current page only, truncated reject_reasons) ───────────
    start = (page - 1) * page_size
    page_df = df.iloc[start : start + page_size].copy()
    page_df["reject_reasons"] = page_df["reject_reasons"].apply(_truncate)

    st.dataframe(
        page_df[["timestamp", "pair", "entry_triggered", "confluence_score", "reject_reasons"]],
        use_container_width=True,
    )
    st.divider()

    # Reject breakdown uses full filtered df, not just current page
    _render_reject_breakdown(df)


def _truncate(val, max_len=80):
    if val is None or (isinstance(val, float) and pd.isna(val)):
        return ""
    text = str(val)
    return text if len(text) <= max_len else text[:max_len] + "…"


def _render_reject_breakdown(df):
    st.subheader("Reject Reason Breakdown")

    rejected = df[df["entry_triggered"] == False].copy()  # noqa: E712

    if rejected.empty:
        st.info("No rejected signals.")
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

    fig = px.pie(reason_counts, names="reason", values="count", hole=0.4)
    fig.update_layout(margin=dict(l=0, r=0, t=10, b=0), height=350)
    st.plotly_chart(fig, use_container_width=True)
