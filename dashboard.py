import time
import os

import streamlit as st
import psycopg2
from dotenv import load_dotenv

from components import overview, trades, signals, futures, portfolio

load_dotenv()

st.set_page_config(
    page_title="bot-spot-btc dashboard",
    page_icon="📊",
    layout="wide",
)

REFRESH_INTERVAL = 60  # seconds


def get_connection():
    return psycopg2.connect(
        host=os.getenv("DB_HOST", "localhost"),
        port=int(os.getenv("DB_PORT", 5432)),
        dbname=os.getenv("DB_NAME"),
        user=os.getenv("DB_USER"),
        password=os.getenv("DB_PASSWORD"),
        connect_timeout=5,
    )


def get_connection_futures():
    return psycopg2.connect(
        host=os.getenv("DB2_HOST", "localhost"),
        port=int(os.getenv("DB2_PORT", 5432)),
        dbname=os.getenv("DB2_NAME"),
        user=os.getenv("DB2_USER"),
        password=os.getenv("DB2_PASSWORD"),
        connect_timeout=5,
    )


st.title("bot-spot-btc — Live Dashboard")

try:
    conn_spot = get_connection()
except Exception as e:
    st.error(f"Cannot connect to spot database: {e}")
    st.stop()

conn_futures = None
try:
    conn_futures = get_connection_futures()
except Exception as e:
    st.warning(f"Futures database unavailable: {e}")

tab1, tab2, tab3, tab4, tab5 = st.tabs(
    ["🟢 Spot Overview", "📋 Spot Trades", "📡 Spot Signals", "🔵 Futures", "📊 Portfolio"]
)

with tab1:
    overview.render(conn_spot)

with tab2:
    trades.render(conn_spot)

with tab3:
    signals.render(conn_spot)

with tab4:
    if conn_futures:
        futures.render(conn_futures)
    else:
        st.info("Futures database not connected. Set DB2_* variables in .env.")

with tab5:
    portfolio.render(conn_spot, conn_futures)

conn_spot.close()
if conn_futures:
    conn_futures.close()

# Auto-refresh
st.caption(f"Auto-refreshing every {REFRESH_INTERVAL}s…")
time.sleep(REFRESH_INTERVAL)
st.rerun()
