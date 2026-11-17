"""
Quantum Picks & Shovels — Daily Live Signal
Second Layer Capital

Run manually at your desk before market open, any day of the week.

    python live_signal.py

Prints a complete order sheet. You place the orders manually in Schwab.
Modeled on the nuclear screener's live_signal.py: 60-day momentum filter,
15% drawdown limit, a score gate, equal weights, and a defensive-asset
line for when no names pass (or too few to fill the basket).

OPEN CALLS FOR KEVIN (values below are placeholders, not decisions):
  - SCORE_GATE = 40: same gate as the nuclear live signal. Quantum names
    are earlier-stage and mostly pre-revenue, so a lower gate may fit --
    Kevin's call.
  - ACCOUNT_CAPITAL = $800: same budget as the nuclear live signal.
    Kevin's call.
  - DEFENSIVE = "SGOV": iShares 0-3 Month Treasury Bond ETF. Nuclear's
    live signal uses USFR; SGOV is the pick here because it is the
    defensive asset the nuclear backtester already validated (T-bill
    ladder, no credit risk). Kevin's call -- USFR is the alternative.
  - Runway exclusion: a ticker the scorer flags with a runway flag (any
    flag containing "runway", e.g. a <12-month cash-runway flag) never
    enters the basket, however high it scores.
  - Score None does not fail the gate (same convention as nuclear's live
    signal: an unscored name can still qualify on momentum alone, ranked
    last). The allocator is stricter -- it requires a score >= gate.
"""

import json
import os
from datetime import datetime

import numpy as np
import pandas as pd
import yfinance as yf

from data.fetch_fundamentals import load_fundamentals

try:
    from config.universe import QUANTUM_UNIVERSE, YFINANCE_SYMBOLS
except ImportError:  # running from a different cwd
    try:
        from universe import QUANTUM_UNIVERSE
        YFINANCE_SYMBOLS = {}
    except ImportError:
        QUANTUM_UNIVERSE = {}
        YFINANCE_SYMBOLS = {}

ACCOUNT_CAPITAL = 800.00
MIN_POSITIONS = 4
MAX_POSITIONS = 6
MOMENTUM_WINDOW = 60
DRAWDOWN_LIMIT = 0.15
SCORE_GATE = 40
LIMIT_OFFSET = 0.005
DEFENSIVE = "SGOV"

TICKERS = list(QUANTUM_UNIVERSE)

STATE_PATH = os.path.join(os.path.dirname(__file__), "signal_state.json")
LOOKBACK_DAYS = 120


def load_prices():
    all_tickers = TICKERS + [DEFENSIVE]
    print(f"  [DATA] Pulling {LOOKBACK_DAYS}-day price history...")
    raw = yf.download(
        all_tickers,
        period=f"{LOOKBACK_DAYS}d",
        auto_adjust=True,
        progress=False,
    )["Close"]
    raw = raw.ffill().dropna(how="all")
    eq = raw[TICKERS].copy()
    return eq, raw[DEFENSIVE]


def load_scores():
    """Returns (scores, coverage): final score per ticker and bucket
    coverage ("n/m" — buckets actually scored / buckets possible), so a
    one-bucket 100 cannot be mistaken for a full-coverage 100 on the
    order sheet. Runway-flagged tickers are reported and excluded here."""
    scores = {}
    coverage = {}
    try:
        from scoring.quantum_scorer import calculate_scores
    except ImportError as e:
        print(f"  [SCORE] Warning: scorer not available ({e})")
        return scores, coverage
    fundamentals = load_fundamentals(TICKERS)
    try:
        results = calculate_scores(fundamentals)
    except Exception as e:
        print(f"  [SCORE] Warning: scorer failed ({e})")
        return scores, coverage
    for r in results:
        ticker = r["ticker"]
        flags = r.get("flags") or []
        if any("runway" in str(f).lower() for f in flags):
            print(f"  [SCORE] {ticker}: runway-flagged, excluded from basket.")
            continue
        scores[ticker] = r.get("final_score")
        coverage[ticker] = (
            f"{r.get('bucket_count')}/{r.get('buckets_possible')}"
            if r.get("bucket_count") is not None else "--"
        )
    return scores, coverage


def load_state():
    if os.path.exists(STATE_PATH):
        with open(STATE_PATH) as f:
            return json.load(f)
    return {"last_basket": [], "last_run": None}


def save_state(basket):
    state = {"last_basket": basket, "last_run": datetime.today().strftime("%Y-%m-%d")}
    with open(STATE_PATH, "w") as f:
        json.dump(state, f, indent=2)


def build_signal(equity_prices, scores, coverage=None):
    if len(equity_prices) < MOMENTUM_WINDOW + 1:
        print("  [SIGNAL] Not enough price history.")
        return []

    qualifying = []
    for ticker in TICKERS:
        col = equity_prices[ticker]
        if col.isna().all():
            continue
        current_price = col.iloc[-1]
        lookback_price = col.iloc[-(MOMENTUM_WINDOW + 1)]
        if pd.isna(current_price) or pd.isna(lookback_price):
            continue
        momentum = (current_price / lookback_price) - 1.0
        if momentum <= 0:
            continue
        peak = col.dropna().max()
        drawdown = (current_price - peak) / peak
        if drawdown <= -DRAWDOWN_LIMIT:
            continue
        score = scores.get(ticker)
        if score is not None and score < SCORE_GATE:
            continue
        qualifying.append({
            "ticker": ticker,
            "score": score if score is not None else "--",
            "buckets": (coverage or {}).get(ticker, "--"),
            "momentum": round(momentum * 100, 1),
            "drawdown": round(drawdown * 100, 1),
            "price": round(current_price, 2),
        })

    qualifying.sort(key=lambda x: (x["score"] == "--", -(x["score"] if x["score"] != "--" else 0)))
    return qualifying[:MAX_POSITIONS]


def build_order_sheet(basket, defensive_price):
    orders = []
    n_equity = len(basket)
    n_def = max(0, MIN_POSITIONS - n_equity)
    n_total = n_equity + n_def
    pos_size = ACCOUNT_CAPITAL / n_total if n_total > 0 else ACCOUNT_CAPITAL

    for item in basket:
        limit_price = round(item["price"] * (1 + LIMIT_OFFSET), 2)
        shares = int(pos_size / limit_price)
        orders.append({
            "ticker": item["ticker"],
            "score": item["score"],
            "buckets": item.get("buckets", "--"),
            "momentum": item["momentum"],
            "drawdown": item["drawdown"],
            "last_close": item["price"],
            "limit_price": limit_price,
            "shares": shares,
            "actual_cost": round(shares * limit_price, 2),
            "type": "EQUITY",
        })

    if n_def > 0:
        defensive_allocation = pos_size * n_def
        limit_price = round(defensive_price * (1 + LIMIT_OFFSET), 2)
        shares = int(defensive_allocation / limit_price)
        orders.append({
            "ticker": DEFENSIVE,
            "score": "--",
            "buckets": "--",
            "momentum": "--",
            "drawdown": "--",
            "last_close": round(defensive_price, 2),
            "limit_price": limit_price,
            "shares": shares,
            "actual_cost": round(shares * limit_price, 2),
            "type": "DEFENSIVE",
        })

    return orders


def get_changes(current_orders, last_basket):
    current_tickers = [o["ticker"] for o in current_orders]
    added = [t for t in current_tickers if t not in last_basket]
    removed = [t for t in last_basket if t not in current_tickers]
    return added, removed


def print_divider(char="-", width=68):
    print(char * width)


def print_report(orders, added, removed, state):
    today = datetime.today().strftime("%Y-%m-%d %H:%M")
    last_run = state.get("last_run", "never")
    n_eq = sum(1 for o in orders if o["type"] == "EQUITY")
    n_def = sum(1 for o in orders if o["type"] == "DEFENSIVE")

    print()
    print_divider("=")
    print("  SECOND LAYER CAPITAL -- QUANTUM PICKS & SHOVELS")
    print("  Daily Live Signal  |  60-Day Momentum  |  Score Gate >= 40")
    print(f"  Generated : {today}")
    print(f"  Prior run : {last_run}")
    print(f"  Capital   : ${ACCOUNT_CAPITAL:,.2f}  |  {n_eq} equity + {n_def} defensive")
    print_divider("=")
    print()

    if added or removed:
        print("  CHANGES FROM PRIOR RUN:")
        for t in added:
            print(f"    + {t}  (entering basket)")
        for t in removed:
            print(f"    - {t}  (exiting basket -- close this position)")
        print()
    elif last_run != "never":
        print("  No changes from prior run. Basket is unchanged.")
        print()

    print("  ORDER SHEET -- Enter in Schwab before market open")
    print(f"  Order type: BUY LIMIT  |  Duration: DAY  |  Offset: +{LIMIT_OFFSET * 100:.1f}% above prior close")
    print()
    print(f"  {'TICKER':<8} {'TYPE':<10} {'SCORE':<6} {'BKTS':<6} {'MOM%':<8} {'DD%':<8} {'CLOSE':<8} {'LIMIT':<8} {'SHARES':<8} {'COST'}")
    print_divider()

    total_deployed = 0
    for o in orders:
        score_str = str(o["score"])
        mom_str = f"{o['momentum']}%" if o["momentum"] != "--" else "--"
        dd_str = f"{o['drawdown']}%" if o["drawdown"] != "--" else "--"
        print(f"  {o['ticker']:<8} {o['type']:<10} {score_str:<6} {str(o.get('buckets', '--')):<6} {mom_str:<8} {dd_str:<8} ${o['last_close']:<7} ${o['limit_price']:<7} {o['shares']:<8} ${o['actual_cost']}")
        total_deployed += o["actual_cost"]

    print_divider()
    cash_remaining = round(ACCOUNT_CAPITAL - total_deployed, 2)
    print(f"  Total deployed : ${total_deployed:,.2f}")
    print(f"  Cash remaining : ${cash_remaining:,.2f}")
    print()

    if removed:
        print("  SELL INSTRUCTIONS -- Close these before placing new orders:")
        for t in removed:
            print(f"    SELL ALL shares of {t} -- MARKET ORDER at open")
        print()

    print("  REMINDERS:")
    print("    Stop-loss   : Sell if any position drops 15% from your entry price.")
    print("    Take-profit : Sell if any position doubles from your entry price.")
    print()
    print_divider("=")
    print()


def main():
    print()
    print_divider("=")
    print("  QUANTUM PICKS & SHOVELS SCREENER -- LIVE SIGNAL")
    print(f"  {datetime.today().strftime('%Y-%m-%d %H:%M')}")
    print_divider("=")
    print()

    equity_prices, defensive_prices = load_prices()
    defensive_last_close = defensive_prices.iloc[-1]

    print(f"  [DATA] {len(equity_prices)} trading days loaded. Latest close: {equity_prices.index[-1].strftime('%Y-%m-%d')}")

    print("  [SCORE] Loading quantum scores...")
    scores, coverage = load_scores()
    scored = {t: v for t, v in scores.items() if v is not None}
    print(f"  [SCORE] {len(scored)}/{len(TICKERS)} tickers scored. Gate >= {SCORE_GATE}.")

    print(f"  [SIG]  Running {MOMENTUM_WINDOW}-day momentum filter + score gate...")
    basket = build_signal(equity_prices, scores, coverage)

    if not basket:
        print(f"  [SIG]  No tickers passed all filters. Full allocation to {DEFENSIVE}.")
    else:
        print(f"  [SIG]  {len(basket)} tickers qualify: {', '.join(b['ticker'] for b in basket)}")

    orders = build_order_sheet(basket, defensive_last_close)

    state = load_state()
    last_basket = state.get("last_basket", [])
    added, removed = get_changes(orders, last_basket)

    print_report(orders, added, removed, state)

    save_state([o["ticker"] for o in orders])
    print("  Signal state saved to signal_state.json")
    print()


if __name__ == "__main__":
    main()
