# bot-spot-btc-dashboard

Read-only Streamlit dashboard for monitoring bot-spot-btc trading activity.

## Stack
- Python + Streamlit
- psycopg2 (PostgreSQL driver)
- pandas
- plotly

## Database
- Reads from PostgreSQL (see `.env` for connection details)
- Tables: `trades`, `signals`, `candles`
- Schema reference: `../bot-spot-btc/PRD.md`

## Deployment
- Runs as a systemd service: `bot-spot-btc-dashboard.service`
- Service file is in the project root; install to `/etc/systemd/system/`
- Managed via `systemctl` — `enable --now` starts it on boot

## Hard Rules
- **NO write operations to the database** — SELECT queries only
- **NO ccxt** — no exchange library imports
- **NO Bybit API calls** — no external exchange connections
- All queries must be wrapped in try-except with graceful empty state handling
