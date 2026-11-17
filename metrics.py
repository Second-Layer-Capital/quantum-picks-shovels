"""
Second Layer Capital — Quantum Portfolio Performance Metrics
Analyzes the paper-trade ledger (data/trade_log.csv) against live
market prices. Modeled on the nuclear screener's metrics.py, with
two corrections:

  1. An EMPTY log returns zeros and prints "no data" — it does not
     crash, and it does not print a summary over zero trades.
  2. A SELL row is NOT counted as an investment. Only BUY rows add
     to total invested; a SELL reduces the net share count. (The
     nuclear version added every row's Allocation_Dollar to invested,
     so a sell inflated the invested figure.)
  3. On a price-fetch failure, the affected ticker's trades are
     dropped from the current-value total and the ticker is NAMED —
     never silently valued at $0.00, and never at an invented price.

Ledger columns: date, ticker, action, shares, price, total.
"""

import csv
import os

import yfinance as yf

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
LOG_FILE = os.path.join(BASE_DIR, "data", "trade_log.csv")

# Yahoo Finance symbol overrides (ASMI delisted from Nasdaq; live listing
# is Euronext ASM.AS).
try:
    from config.universe import YFINANCE_SYMBOLS
except ImportError:  # running from a different cwd
    try:
        from universe import YFINANCE_SYMBOLS
    except ImportError:
        YFINANCE_SYMBOLS = {}


def fetch_live_price(ticker):
    """Latest close for one ticker. Raises on any failure — the
    caller decides what a failed fetch means (drop, don't invent)."""
    asset = yf.Ticker(YFINANCE_SYMBOLS.get(ticker, ticker))
    close = asset.history(period="1d")["Close"]
    return float(close.iloc[-1])


def read_trades(log_file=None):
    """Read the ledger into a list of row dicts.

    Returns [] when the file is missing or has no rows. Malformed
    rows (bad numbers, unknown action) are skipped with a printed
    warning, never silently counted.
    """
    path = log_file or LOG_FILE
    if not os.path.exists(path):
        return []
    trades = []
    with open(path, mode="r", newline="") as f:
        reader = csv.DictReader(f)
        for row in reader:
            try:
                action = str(row["action"]).upper()
                if action not in ("BUY", "SELL"):
                    raise ValueError(f"unknown action {row['action']!r}")
                trades.append({
                    "date": row.get("date", ""),
                    "ticker": str(row["ticker"]).upper(),
                    "action": action,
                    "shares": float(row["shares"]),
                    "price": float(row["price"]),
                    "total": float(row["total"]) if row.get("total") not in (None, "") else 0.0,
                })
            except Exception as e:
                print(f"[METRICS] Skipping malformed ledger row {row}: {e}")
    return trades


def compute_metrics(log_file=None, price_fetcher=None):
    """Portfolio metrics from the trade log. Never crashes on an
    empty or missing log — returns zeros.

    price_fetcher(ticker) -> float is injectable for tests; defaults
    to a live yfinance fetch. A fetcher failure drops that ticker's
    trades from the current-value total and records the ticker in
    "price_fetch_failures" (printed by the caller).

    Returns a dict with: total_invested, total_current_value,
    total_profit_loss, total_return_pct, win_rate, winning_trades,
    trades_evaluated, buy_count, sell_count, tickers,
    price_fetch_failures, per_trade (list of evaluated BUY rows).
    """
    fetcher = price_fetcher or fetch_live_price
    trades = read_trades(log_file)

    result = {
        "total_invested": 0.0,
        "total_current_value": 0.0,
        "total_profit_loss": 0.0,
        "total_return_pct": 0.0,
        "win_rate": 0.0,
        "winning_trades": 0,
        "trades_evaluated": 0,
        "buy_count": 0,
        "sell_count": 0,
        "tickers": [],
        "price_fetch_failures": [],
        "per_trade": [],
    }
    if not trades:
        return result

    net_shares = {}
    invested_by_ticker = {}
    for trade in trades:
        ticker = trade["ticker"]
        if trade["action"] == "BUY":
            result["buy_count"] += 1
            # Prefer the logged total; fall back to shares * price.
            total = trade["total"] or round(trade["shares"] * trade["price"], 2)
            result["total_invested"] += total
            invested_by_ticker[ticker] = invested_by_ticker.get(ticker, 0.0) + total
            net_shares[ticker] = net_shares.get(ticker, 0.0) + trade["shares"]
        else:  # SELL — reduces the position; NOT an investment.
            result["sell_count"] += 1
            net_shares[ticker] = net_shares.get(ticker, 0.0) - trade["shares"]

    result["tickers"] = sorted(net_shares.keys())

    # Current value: net shares x live price, per ticker. A failed
    # fetch drops that ticker from the total — and says so.
    live_prices = {}
    for ticker, shares in net_shares.items():
        if shares == 0:
            continue
        try:
            live_prices[ticker] = fetcher(ticker)
        except Exception as e:
            result["price_fetch_failures"].append(ticker)
            print(f"[METRICS] Price fetch failed for {ticker} ({e}) — "
                  f"its {shares} net shares are EXCLUDED from current "
                  f"value (no price invented).")

    for ticker, shares in net_shares.items():
        if shares == 0 or ticker not in live_prices:
            continue
        result["total_current_value"] += shares * live_prices[ticker]

    # Win rate over BUY trades that could be valued live.
    for trade in trades:
        if trade["action"] != "BUY":
            continue
        ticker = trade["ticker"]
        if ticker not in live_prices:
            continue
        live_price = live_prices[ticker]
        entry_price = trade["price"]
        trade_return_pct = ((live_price - entry_price) / entry_price) * 100 \
            if entry_price else 0.0
        result["trades_evaluated"] += 1
        if trade_return_pct > 0:
            result["winning_trades"] += 1
        result["per_trade"].append({
            "ticker": ticker,
            "shares": trade["shares"],
            "entry_price": entry_price,
            "live_price": live_price,
            "return_pct": round(trade_return_pct, 2),
        })

    result["total_profit_loss"] = (
        result["total_current_value"] - result["total_invested"])
    if result["total_invested"] > 0:
        result["total_return_pct"] = (
            result["total_profit_loss"] / result["total_invested"] * 100)
    if result["trades_evaluated"] > 0:
        result["win_rate"] = (
            result["winning_trades"] / result["trades_evaluated"] * 100)
    return result


def run_performance_analysis(log_file=None, price_fetcher=None):
    """Print the portfolio summary. Returns the metrics dict."""
    path = log_file or LOG_FILE
    if not os.path.exists(path):
        print("No trade log file found yet. No data — execute a paper "
              "trade via logger.py first.")
        return compute_metrics(log_file=path, price_fetcher=price_fetcher)

    metrics = compute_metrics(log_file=path, price_fetcher=price_fetcher)

    if metrics["buy_count"] == 0 and metrics["sell_count"] == 0:
        print("The trade log is currently empty — no data.")
        return metrics

    print("Reading transaction history from ledger...")
    print(f"\n==========================================================")
    print(f"         SECOND LAYER CAPITAL — PERFORMANCE METRICS        ")
    print(f"==========================================================")
    print(f"{'TICKER':<8}{'SHARES':<10}{'ENTRY_PX':<10}{'LIVE_PX':<10}{'RETURN %'}")
    print("-" * 58)
    for trade in metrics["per_trade"]:
        print(f"{trade['ticker']:<8}{trade['shares']:<10.2f}"
              f"${trade['entry_price']:<9.2f}${trade['live_price']:<9.2f}"
              f"{trade['return_pct']:+.2f}%")
    if metrics["price_fetch_failures"]:
        print(f"  (excluded — price fetch failed: "
              f"{', '.join(metrics['price_fetch_failures'])})")

    print(f"==========================================================")
    print(f"  PORTFOLIO SUMMARY STATISTICS:")
    print(f"  - Total Capital Invested : ${metrics['total_invested']:,.2f} "
          f"(BUY rows only; SELL rows do not count as investment)")
    print(f"  - Current Net Asset Val  : ${metrics['total_current_value']:,.2f}")
    print(f"  - Total Unrealized PnL   : ${metrics['total_profit_loss']:+,.2f} "
          f"({metrics['total_return_pct']:+.2f}%)")
    print(f"  - Win Rate Percentage    : {metrics['win_rate']:.1f}% "
          f"({metrics['winning_trades']}/{metrics['trades_evaluated']} "
          f"Successful Trades)")
    print(f"  - Trades: {metrics['buy_count']} BUY, {metrics['sell_count']} SELL")
    print(f"==========================================================")
    return metrics


if __name__ == "__main__":
    run_performance_analysis()
