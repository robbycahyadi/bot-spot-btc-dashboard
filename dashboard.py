import time
import os

import streamlit as st
import psycopg2
from dotenv import load_dotenv

from components import overview, trades, signals

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


st.title("bot-spot-btc — Live Dashboard")

try:
    conn = get_connection()
except Exception as e:
    st.error(f"Cannot connect to database: {e}")
    st.stop()

tab1, tab2, tab3 = st.tabs(["Overview", "Trade History", "Signal Log"])

with tab1:
    overview.render(conn)

with tab2:
    trades.render(conn)

with tab3:
    signals.render(conn)

conn.close()

# Auto-refresh
st.caption(f"Auto-refreshing every {REFRESH_INTERVAL}s…")
time.sleep(REFRESH_INTERVAL)
st.rerun()
