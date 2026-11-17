"""
Pulls automatable fundamental data for quantum scoring via yfinance.

Replaces the old ingestion.py approach (malformed SEC URL + hardcoded
fallback profiles). There are no fallbacks here: a value that cannot be
fetched is None, and a ticker whose fetch fails entirely returns None.

Covers the quantum scorer's inputs:
  - revenue, research_and_development, gross_profit (latest annual filing)
  - total_cash (latest)
  - annual_burn_rate: absolute value of annual operating cash flow when
    negative, else 0 (a cash-generating name has no burn). None when the
    cash-flow statement cannot be read.
  - revenue_growth: computed year-over-year from the annual financials
    ((latest - prior) / prior). None when fewer than two annual revenue
    figures are available. NEVER a hardcoded number.
  - shares_outstanding (current, from info) and
    shares_outstanding_prior_year (prior-year balance-sheet share count,
    for the scorer's dilution factor). None when unavailable.

The module also provides the allocator's technical filter
(fetch_technical_signals): RSI-14 (Wilder's smoothing), the 50-day simple
moving average, and the latest close price -- modeled exactly on the
nuclear screener's data/fetch_fundamentals.py.
"""

import json
import os
import time

import yfinance as yf

try:
    from config.settings import DATA_FOLDER, RATE_LIMIT_DELAY
except ImportError:  # pragma: no cover - running from a different cwd
    try:
        from settings import DATA_FOLDER, RATE_LIMIT_DELAY
    except ImportError:
        DATA_FOLDER = os.path.join(os.path.dirname(__file__), "..", "data_storage")
        RATE_LIMIT_DELAY = 1.0

try:
    from config.universe import QUANTUM_UNIVERSE, YFINANCE_SYMBOLS
except ImportError:  # running from a different cwd
    try:
        from universe import QUANTUM_UNIVERSE
        YFINANCE_SYMBOLS = {}
    except ImportError:
        QUANTUM_UNIVERSE = {}
        YFINANCE_SYMBOLS = {}


def _clean(value):
    """None for None/NaN; otherwise the value as a float (or int for counts)."""
    if value is None:
        return None
    try:
        import math

        if isinstance(value, float) and math.isnan(value):
            return None
    except Exception:
        pass
    return value


def _first_row_value(frame, labels):
    """Most recent value for the first matching row label, else None."""
    if frame is None:
        return None
    try:
        for label in labels:
            if label in frame.index:
                series = frame.loc[label].dropna()
                if len(series):
                    return _clean(series.iloc[0])
    except Exception:
        pass
    return None


def _nth_row_value(frame, labels, n):
    """Value n columns back (0 = most recent) for the first matching label."""
    if frame is None:
        return None
    try:
        for label in labels:
            if label in frame.index:
                series = frame.loc[label].dropna()
                if len(series) > n:
                    return _clean(series.iloc[n])
    except Exception:
        pass
    return None


def _yf_symbol(ticker: str) -> str:
    """Yahoo Finance symbol for a universe ticker.

    ASMI delisted from Nasdaq; its live listing is Euronext ASM.AS.
    """
    return YFINANCE_SYMBOLS.get(ticker, ticker)


def fetch_fundamentals(ticker: str) -> dict | None:
    """Latest annual fundamentals for one ticker via yfinance.

    Returns a dict with keys revenue, research_and_development,
    gross_profit, total_cash, annual_burn_rate, revenue_growth,
    shares_outstanding, shares_outstanding_prior_year. Any individual
    value that cannot be fetched is None. Returns None (and prints a
    clear error) when nothing usable can be fetched at all -- never
    invented data.
    """
    try:
        t = yf.Ticker(_yf_symbol(ticker))
        info = t.info or {}
    except Exception as e:
        print(f"  [ERROR] {ticker}: could not fetch fundamentals ({e})")
        return None

    try:
        fin = t.financials
    except Exception:
        fin = None
    try:
        cf = t.cashflow
    except Exception:
        cf = None
    try:
        bs = t.balance_sheet
    except Exception:
        bs = None

    revenue = _first_row_value(fin, ["Total Revenue"])
    rd = _first_row_value(
        fin, ["Research And Development", "Research And Development Expense"]
    )
    gross_profit = _first_row_value(fin, ["Gross Profit"])

    total_cash = _clean(info.get("totalCash"))
    if total_cash is None:
        total_cash = _first_row_value(
            bs, ["Cash And Cash Equivalents", "Cash"]
        )

    # Annual burn: |operating cash flow| when the latest annual OCF is
    # negative, else 0 (cash-generating). None when unreadable.
    operating_cf = _first_row_value(
        cf, ["Operating Cash Flow", "Total Cash From Operating Activities"]
    )
    if operating_cf is None:
        annual_burn_rate = None
    elif operating_cf < 0:
        annual_burn_rate = abs(operating_cf)
    else:
        annual_burn_rate = 0

    # Revenue growth, computed YoY from the annual financials only.
    revenue_prior = _nth_row_value(fin, ["Total Revenue"], 1)
    if revenue is not None and revenue_prior not in (None, 0):
        revenue_growth = (revenue - revenue_prior) / revenue_prior
    else:
        revenue_growth = None

    shares_outstanding = _clean(info.get("sharesOutstanding"))
    shares_outstanding_prior_year = _nth_row_value(
        bs, ["Ordinary Shares Number", "Share Issued"], 1
    )

    result = {
        "revenue": revenue,
        "research_and_development": rd,
        "gross_profit": gross_profit,
        "total_cash": total_cash,
        "annual_burn_rate": annual_burn_rate,
        "revenue_growth": revenue_growth,
        "shares_outstanding": shares_outstanding,
        "shares_outstanding_prior_year": shares_outstanding_prior_year,
    }

    if all(v is None for v in result.values()):
        print(f"  [ERROR] {ticker}: no usable fundamental data returned")
        return None
    return result


def load_fundamentals(tickers, use_cache=True) -> dict:
    """Fundamentals for each ticker: live fetch first, cached
    data_storage/<TICKER>_data.json second (real past fetch, not a
    fixture), None when neither is available."""
    fundamentals = {}
    for ticker in tickers:
        data = fetch_fundamentals(ticker)
        if data is None and use_cache:
            path = os.path.join(DATA_FOLDER, f"{ticker}_data.json")
            if os.path.exists(path):
                try:
                    with open(path) as f:
                        data = json.load(f)
                    print(f"  [CACHE] {ticker}: live fetch failed, using {path}")
                except Exception as e:
                    print(f"  [ERROR] {ticker}: cached file unreadable ({e})")
                    data = None
        fundamentals[ticker] = data
        time.sleep(RATE_LIMIT_DELAY)
    return fundamentals


# -- Technical signals (allocator.py's RSI / 50-SMA filter) --------------------
#
# Modeled exactly on the nuclear screener's version. RSI-14 uses Wilder's
# smoothing (the standard): the first average gain/loss is the simple mean
# of the first 14 changes, then each step is
# avg = (prev_avg * 13 + current) / 14.

RSI_PERIOD = 14
SMA_PERIOD = 50
TECHNICAL_HISTORY_PERIOD = "6mo"  # ~126 trading days: warm-up for both signals
MIN_CLOSES = SMA_PERIOD + 1  # 50 closes for the SMA, plus the current close

_NONE_SIGNALS = {"close_price": None, "rsi_14": None, "above_50_sma": None}


def _wilder_rsi(closes, period=RSI_PERIOD):
    """Wilder's RSI over closes, oldest first. Needs period + 1 values.

    Returns None when there are too few closes. When there are no down-moves
    at all the RSI is 100.0 if there was any up-move, else 50.0 (flat prices
    are neutral, not overbought).
    """
    values = [float(c) for c in closes]
    if len(values) < period + 1:
        return None

    gains = []
    losses = []
    for prev, cur in zip(values, values[1:]):
        change = cur - prev
        gains.append(change if change > 0 else 0.0)
        losses.append(-change if change < 0 else 0.0)

    avg_gain = sum(gains[:period]) / period
    avg_loss = sum(losses[:period]) / period
    for gain, loss in zip(gains[period:], losses[period:]):
        avg_gain = (avg_gain * (period - 1) + gain) / period
        avg_loss = (avg_loss * (period - 1) + loss) / period

    if avg_loss == 0:
        return 100.0 if avg_gain > 0 else 50.0
    rs = avg_gain / avg_loss
    return 100.0 - (100.0 / (1.0 + rs))


def _technical_signals_from_closes(closes) -> dict:
    """Pure computation from daily closes (oldest first).

    Returns {"close_price", "rsi_14", "above_50_sma"}. When fewer than
    MIN_CLOSES closes are available all three are None -- the caller treats
    that as no usable price data.
    """
    try:
        import pandas as pd

        if isinstance(closes, pd.Series):
            values = closes.dropna().astype(float).tolist()
        else:
            values = [float(c) for c in closes]
    except (TypeError, ValueError):
        return dict(_NONE_SIGNALS)

    if len(values) < MIN_CLOSES:
        return dict(_NONE_SIGNALS)

    close_price = values[-1]
    sma_50 = sum(values[-SMA_PERIOD:]) / SMA_PERIOD
    return {
        "close_price": close_price,
        "rsi_14": _wilder_rsi(values),
        "above_50_sma": close_price > sma_50,
    }


def fetch_technical_signals(ticker: str) -> dict:
    """RSI-14, 50-day SMA status, and latest close for one ticker.

    Pulls ~6 months of daily closes via yfinance. On any fetch failure, or
    when too few closes come back, returns all Nones instead of raising --
    allocator.py prints DATA ERROR for that ticker and moves on.
    """
    try:
        t = yf.Ticker(_yf_symbol(ticker))
        hist = t.history(period=TECHNICAL_HISTORY_PERIOD, interval="1d")
        if hist is None or hist.empty or "Close" not in hist.columns:
            return dict(_NONE_SIGNALS)
        closes = hist["Close"].dropna()
        if len(closes) < MIN_CLOSES:
            return dict(_NONE_SIGNALS)
        return _technical_signals_from_closes(closes)
    except Exception:
        return dict(_NONE_SIGNALS)


def fetch_momentum_drawdown(ticker: str, window: int = 60) -> tuple:
    """60-day momentum and drawdown-from-peak (as fractions) for one ticker.

    Returns (momentum, drawdown), each None on any fetch failure or when
    too few closes come back. Used by the allocator / live signal order
    sheets; never raises.
    """
    try:
        t = yf.Ticker(_yf_symbol(ticker))
        hist = t.history(period=TECHNICAL_HISTORY_PERIOD, interval="1d")
        if hist is None or hist.empty or "Close" not in hist.columns:
            return (None, None)
        closes = hist["Close"].dropna().astype(float).tolist()
        if len(closes) < window + 1:
            return (None, None)
        current = closes[-1]
        lookback = closes[-(window + 1)]
        peak = max(closes)
        if lookback == 0 or peak == 0:
            return (None, None)
        return ((current / lookback) - 1.0, (current - peak) / peak)
    except Exception:
        return (None, None)


if __name__ == "__main__":
    os.makedirs(DATA_FOLDER, exist_ok=True)
    print(f"Fetching fundamentals for {len(QUANTUM_UNIVERSE)} tickers...")
    for ticker in QUANTUM_UNIVERSE:
        print(f" -> {ticker}")
        data = fetch_fundamentals(ticker)
        if data is None:
            print(f"    [SKIP] {ticker}: no data fetched, nothing written")
            continue
        data["ticker"] = ticker
        file_path = os.path.join(DATA_FOLDER, f"{ticker}_data.json")
        with open(file_path, "w") as f:
            json.dump(data, f, indent=4)
        print(f"    [OK] wrote {file_path}")
        time.sleep(RATE_LIMIT_DELAY)
    print("\n[✓] Fetch complete.")
