# bot-spot-btc-dashboard

Read-only Streamlit dashboard for monitoring bot-spot-btc trading activity.

## Features
- **Overview** — summary metrics (total trades, winrate, profit factor, total PnL), equity curve, open positions
- **Trade History** — closed trades table with filters by pair and outcome
- **Signal Log** — all signals including rejected ones, with reject reason breakdown

## Setup

### 1. Clone / copy the project
```bash
cd ~/projects
git clone <repo-url> bot-spot-btc-dashboard
cd bot-spot-btc-dashboard
```

### 2. Create a virtual environment
```bash
python3 -m venv .venv
source .venv/bin/activate
```

### 3. Install dependencies
```bash
pip install -r requirements.txt
```

### 4. Configure environment
```bash
cp .env.example .env
# Edit .env and fill in DB_USER and DB_PASSWORD
nano .env
```

### 5. Run the dashboard
```bash
streamlit run dashboard.py
```

The dashboard opens at `http://localhost:8501` and auto-refreshes every 60 seconds.

## Running as a systemd service

Install and enable the included service unit so the dashboard starts automatically on boot:

```bash
sudo cp bot-spot-btc-dashboard.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable --now bot-spot-btc-dashboard
```

Check status and logs:

```bash
sudo systemctl status bot-spot-btc-dashboard
journalctl -u bot-spot-btc-dashboard -f
```

## Database
Connects to PostgreSQL using credentials in `.env`. Reads from tables: `trades`, `signals`, `candles`.

This dashboard is **read-only** — it never writes to the database.
