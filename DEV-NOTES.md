# DEV-NOTES — bot-spot-btc-dashboard

## 2026-06-09 — Paginasi semua tabel

### What changed

Semua tabel `st.dataframe` kini punya paginasi seragam: tombol **← Prev** / **Next →**, info halaman, dan selectbox **Baris per halaman** (25 / 50 / 100). Page state di `st.session_state`; ganti filter otomatis reset ke halaman 1.

| File | Fungsi | Session key prefix |
|------|--------|--------------------|
| `signals.py` | `render` (signal log) | `sig_` |
| `trades.py` | `render` (spot trade history) | `spt_tr_` |
| `overview.py` | `_render_open_positions` | `spt_pos_` |
| `futures.py` | `_render_open_positions` | `fut_pos_` |
| `futures.py` | `_render_trade_history` | `fut_tr_` |
| `futures.py` | `_render_signal_log` | `fut_sig_` |

- `portfolio.py` `_render_bot_summary_table` dikecualikan — hanya 2 baris (per bot), paginasi tidak relevan.
- CSV download (signal log) dan reject breakdown pie chart tetap menggunakan **seluruh data terfilter**, bukan hanya halaman aktif.

---

## 2026-06-09 — Spot signal log fix + Futures signal log filter update

### What changed

**`components/signals.py` — bug fix**
- Reverted SELECT to only columns that exist in the spot `signals` table: `timestamp`, `pair`, `entry_triggered`, `confluence_score`, `reject_reasons`.
- Removed `signal_type`, `bias_direction`, `temperature` — these columns do **not** exist in the spot DB and caused a PostgreSQL error.
- Display table now shows 5 columns: timestamp, pair, entry_triggered, confluence_score, reject_reasons.
- All filters (date range, pair, entry triggered, row limit) and CSV export retained.

**`components/futures.py` — `_render_signal_log` updated to match spot UX**
- Added date range filter (Dari / Sampai), default last 7 days; applied in SQL `WHERE timestamp::date BETWEEN`.
- Added Pair filter selectbox: All / BTC/USDT / ETH/USDT.
- Added Entry Triggered filter: All / Entry only / Rejected only.
- Added Bias Direction filter: All / LONG / SHORT / NEUTRAL.
- Added row limit selectbox: 50 / 100 / 500 / All, default 50.
- Added CSV download button — filename: `futures_signals_{pair}_{date_from}_{date_to}.csv`.
- `reject_reasons` truncated to 80 chars in display table; full value in CSV.
- Added `_truncate()` helper (same as in `signals.py`).

### Spot signals table schema (confirmed columns only)
`timestamp, pair, entry_triggered, confluence_score, reject_reasons`

### Futures signals table schema
`timestamp, pair, timeframe, signal_type, entry_triggered, bias_direction, temperature, confluence_score, funding_rate, reject_reasons`

## 2026-06-09 — Signal Log filters + CSV export (spot only, original entry)

### What was attempted
- Added `signal_type`, `bias_direction`, `temperature` to spot signal SELECT — these columns do not exist in the spot DB (see fix above).

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
