# DEV-NOTES — bot-spot-btc-dashboard

## 2026-06-07 — Extended to 5-tab multi-bot dashboard

### What changed
- Added support for a second PostgreSQL database (bot-future-btc) via `DB2_*` env vars.
- `dashboard.py`: opens `conn_spot` (DB_*) and `conn_futures` (DB2_*) each render cycle; futures connection is non-fatal (shows warning instead of stopping the app if DB2 is unconfigured).
- Added two new components:
  - `components/futures.py` — full futures tab
  - `components/portfolio.py` — cross-bot aggregate view
- Existing `overview.py`, `trades.py`, `signals.py` are **untouched**.

### Tab layout (5 tabs)
| Tab | Component | DB |
|-----|-----------|----|
| 🟢 Spot Overview | `components/overview.py` | conn_spot |
| 📋 Spot Trades | `components/trades.py` | conn_spot |
| 📡 Spot Signals | `components/signals.py` | conn_spot |
| 🔵 Futures | `components/futures.py` | conn_futures |
| 📊 Portfolio | `components/portfolio.py` | both |

### Futures tab (`components/futures.py`) — function list
| Function | What it renders |
|----------|----------------|
| `render(conn)` | Entry point, calls all sub-functions |
| `_render_summary_metrics(conn)` | Total trades, win rate, profit factor, net PnL after fees, total fees, total funding paid |
| `_render_equity_curve(conn)` | Cumulative net PnL line chart |
| `_render_open_positions(conn)` | Open positions with side, leverage, liquidation_price, SL/TP, margin |
| `_render_trade_history(conn)` | Closed trades with filter by side (LONG/SHORT), pair, outcome; shows gross/net PnL, fees, funding |
| `_render_signal_log(conn)` | Last 500 signals with filter by bias_direction and temperature |
| `_render_futures_reject_breakdown(df)` | Pie chart of reject reasons (called from signal log) |

### Portfolio tab (`components/portfolio.py`) — function list
| Function | What it renders |
|----------|----------------|
| `render(conn_spot, conn_futures)` | Entry point |
| `_fetch_closed_pnl(conn, label)` | Helper: returns `[timestamp_exit, pnl_usd]` df for one bot |
| `_bot_summary_row(conn, label)` | Helper: returns stats dict (trades, winners, winrate, net_pnl) for one bot |
| `_render_combined_metrics(conn_spot, conn_futures)` | Spot PnL / Futures PnL / Combined PnL side-by-side metrics |
| `_render_equity_overlay(conn_spot, conn_futures)` | Spot vs Futures vs Combined equity curve overlay (Plotly) |
| `_render_bot_summary_table(conn_spot, conn_futures)` | Summary table per bot: trades, winners, winrate, net PnL |

### Futures DB schema used (read-only SELECT)
- `trades`: timestamp_entry/exit, pair, side, leverage, liquidation_price, entry/exit price, pnl_usd, gross_pnl_usd, total_fee_usd, funding_rate_paid, sl_price, tp1_price, position_size_usd, margin_used_usd, exit_reason, rr_actual, holding_duration_h
- `signals`: timestamp, pair, timeframe, signal_type, entry_triggered, bias_direction, temperature, confluence_score, funding_rate, reject_reasons

### .env additions
```
DB2_HOST=
DB2_PORT=5432
DB2_NAME=
DB2_USER=
DB2_PASSWORD=
```
Fill in the bot-future-btc PostgreSQL credentials to activate the Futures and Portfolio tabs.
