"""
Quantum Picks & Shovels Screener — Earnings & Milestone Tracker
Second Layer Capital

Quantum version of the nuclear screener's earnings_alert.py.

For each universe ticker it prints:
  1. The next earnings date from yfinance (or "no date found" — and
     if ALL fetches fail, it says the fetch failed; a date is never
     invented), plus
  2. Any hand-entered thesis milestones from data/milestones.json
     (qubit counts, error rates, roadmap items per ticker).

data/milestones.json is HAND-ENTERED thesis data only. There is no
automatic source for qubit counts or roadmap items in this repo, so
no milestone is ever generated, guessed, or fetched — a ticker with
no entry simply has no milestones on file.

    python milestone_tracker.py
"""

import json
import os
import sys
from datetime import datetime

import pandas as pd
import yfinance as yf

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
MILESTONES_PATH = os.path.join(BASE_DIR, "data", "milestones.json")

# Yahoo Finance symbol overrides (ASMI delisted from Nasdaq; live listing
# is Euronext ASM.AS). get_earnings_status looks up the mapped symbol.
try:
    from config.universe import YFINANCE_SYMBOLS
except ImportError:  # running from a different cwd
    try:
        from universe import YFINANCE_SYMBOLS
    except ImportError:
        YFINANCE_SYMBOLS = {}

ALERT_WINDOW = 14
UPCOMING_WINDOW = 30


# ── Universe (same loader as backtester.py — tickers are never hardcoded) ──

def load_universe():
    """Return (tickers, meta). Prefers config/universe.py, falls back
    to root universe.py. See backtester.py for the full contract."""
    here = os.path.dirname(os.path.abspath(__file__))
    if here not in sys.path:
        sys.path.insert(0, here)
    raw = None
    for mod_name in ("config.universe", "universe"):
        try:
            mod = __import__(mod_name, fromlist=["x"])
        except Exception:
            continue
        for attr in ("QUANTUM_UNIVERSE", "UNIVERSE", "TICKERS"):
            if hasattr(mod, attr):
                raw = getattr(mod, attr)
                break
        if raw is not None:
            break
    if raw is None:
        raise RuntimeError(
            "Universe unavailable: neither config/universe.py nor "
            "universe.py could be imported."
        )
    if isinstance(raw, (list, tuple)):
        return list(raw), {t: {} for t in raw}
    if isinstance(raw, dict):
        values = list(raw.values())
        if values and all(
            isinstance(v, dict) and "tickers" in v for v in values
        ):
            tickers, meta = [], {}
            for domain, entry in raw.items():
                for t in entry["tickers"]:
                    tickers.append(t)
                    meta[t] = {"layer": domain}
            return tickers, meta
        return list(raw.keys()), dict(raw)
    raise RuntimeError(f"Universe registry has an unrecognized shape: {type(raw)}")


# ── Earnings dates (parse approach copied from nuclear earnings_alert.py) ──

def parse_calendar_earnings_date(cal, today):
    """Parse the next earnings date out of a yfinance calendar payload.

    Returns the earliest date >= today, or None when the payload has
    no usable future earnings date. Never raises on a malformed
    payload: an unreadable calendar is a "no date" outcome, not a crash.

    Shapes handled (yfinance changed shape between versions):
    - dict (yfinance >= 1.x): {"Earnings Date": [date, ...]} — the
      value is a list, sometimes a range of two dates; element [0]
      is the date Yahoo knows. A scalar is accepted defensively.
    - DataFrame (yfinance <= 0.2.x): an "Earnings Date" row, values
      parsed as timestamps. Duck-typed so this module does not need
      to know which shape it got.
    """
    if cal is None:
        return None

    if isinstance(cal, dict):
        values = cal.get("Earnings Date")
        if values is None:
            return None
        if not isinstance(values, (list, tuple)):
            values = [values]
        dates = []
        for val in values:
            try:
                d = pd.Timestamp(val).date()
                if d >= today:
                    dates.append(d)
            except Exception:
                continue
        return min(dates) if dates else None

    # DataFrame shape — duck-typed.
    if hasattr(cal, "empty") and hasattr(cal, "loc"):
        if cal.empty:
            return None
        if "Earnings Date" in cal.index:
            raw = cal.loc["Earnings Date"]
            values = raw.values.flatten() if hasattr(raw, "values") else [raw]
            dates = []
            for val in values:
                try:
                    d = pd.Timestamp(val).date()
                    if d >= today:
                        dates.append(d)
                except Exception:
                    continue
            return min(dates) if dates else None
        return None

    return None


def get_earnings_status(ticker: str):
    """Return (earnings_datetime | None, status).

    status is one of:
      "ok"           — a future earnings date was found;
      "no_date"      — yfinance answered but has no upcoming date;
      "fetch_failed" — every attempt raised (network down, ticker
                       invalid, Yahoo unreachable). A failed fetch
                       is NOT a missing date, and no date is invented
                       for it.

    Attempts, in order (same as nuclear): (1) info dict earnings
    timestamp, (2) earnings_dates DataFrame, (3) calendar attribute
    (dict in yfinance >= 1.x, DataFrame in older versions).
    """
    today = datetime.today().date()
    attempt_errors = 0
    attempts = 0
    try:
        t = yf.Ticker(YFINANCE_SYMBOLS.get(ticker, ticker))
    except Exception:
        return None, "fetch_failed"

    # Attempt 1: info dict next earnings date
    attempts += 1
    try:
        info = t.info or {}
        ts = info.get("earningsTimestamp") or info.get("earningsTimestampStart")
        if ts:
            d = datetime.fromtimestamp(ts).date()
            if d >= today:
                return datetime.combine(d, datetime.min.time()), "ok"
    except Exception:
        attempt_errors += 1

    # Attempt 2: earnings_dates DataFrame
    attempts += 1
    try:
        ed = t.earnings_dates
        if ed is not None and not ed.empty:
            future = [d.date() for d in ed.index if d.date() >= today]
            if future:
                return datetime.combine(min(future), datetime.min.time()), "ok"
    except Exception:
        attempt_errors += 1

    # Attempt 3: calendar attribute — dict or DataFrame.
    attempts += 1
    try:
        d = parse_calendar_earnings_date(t.calendar, today)
        if d is not None:
            return datetime.combine(d, datetime.min.time()), "ok"
    except Exception:
        attempt_errors += 1

    if attempt_errors == attempts:
        return None, "fetch_failed"
    return None, "no_date"


def get_earnings_date(ticker: str):
    """Next earnings datetime, or None. (Nuclear-compatible wrapper:
    use get_earnings_status() when the caller needs to tell a failed
    fetch apart from a genuinely missing date.)"""
    date, _status = get_earnings_status(ticker)
    return date


def days_until(target: datetime) -> int:
    return (target.date() - datetime.today().date()).days


# ── Hand-entered milestones ───────────────────────────────────────────────────

def load_milestones(path=None):
    """Read data/milestones.json. Returns {ticker: [milestone, ...]}.

    Missing file → {} (no milestones on file, not an error).
    Malformed JSON → warning + {} (never crash the briefing over it).
    Accepts either {"milestones": {ticker: [...]}} or a flat
    {ticker: [...]} shape; keys starting with "_" are template
    comments, not tickers. Every value here is hand-entered by a
    human — this function never invents a milestone.
    """
    path = path or MILESTONES_PATH
    if not os.path.exists(path):
        return {}
    try:
        with open(path) as f:
            data = json.load(f)
    except Exception as e:
        print(f"[MILESTONES] WARNING: {path} unreadable ({e}) — "
              f"milestones skipped, not guessed.")
        return {}
    if not isinstance(data, dict):
        print(f"[MILESTONES] WARNING: {path} is not a JSON object — skipped.")
        return {}
    inner = data.get("milestones", data)
    if not isinstance(inner, dict):
        return {}
    out = {}
    for ticker, items in inner.items():
        if str(ticker).startswith("_"):
            continue
        if isinstance(items, list):
            out[str(ticker).upper()] = items
    return out


# ── Check & report ────────────────────────────────────────────────────────────

def check_milestones(tickers=None):
    """Per-ticker earnings + milestone status. Returns a list of
    dicts: {ticker, earnings_date, days_until, status, milestones}.
    Never raises on a per-ticker failure — a bad ticker is reported
    as fetch_failed, not allowed to abort the rest."""
    if tickers is None:
        tickers, _ = load_universe()
    milestones = load_milestones()
    results = []
    for ticker in tickers:
        try:
            earnings_date, status = get_earnings_status(ticker)
        except Exception as e:
            print(f"[MILESTONES] {ticker}: earnings check raised ({e}) — "
                  f"reported as fetch_failed.")
            earnings_date, status = None, "fetch_failed"
        results.append({
            "ticker": ticker,
            "earnings_date": earnings_date,
            "days_until": days_until(earnings_date) if earnings_date else None,
            "status": status,
            "milestones": milestones.get(ticker, []),
        })
    return results


def print_divider(char="-", width=65):
    print(char * width)


def main():
    tickers, _ = load_universe()
    print()
    print_divider("=")
    print("  SECOND LAYER CAPITAL -- EARNINGS & MILESTONE TRACKER")
    print(f"  Quantum Picks & Shovels  |  {datetime.today().strftime('%Y-%m-%d')}")
    print(f"  Tracking: {', '.join(tickers)}")
    print_divider("=")
    print()

    results = check_milestones(tickers)

    n_failed = sum(1 for r in results if r["status"] == "fetch_failed")
    if n_failed == len(results) and results:
        print("!" * 65)
        print("!!! EARNINGS FETCH FAILED for every ticker — yfinance did")
        print("!!! not return usable data. No dates below are real; none")
        print("!!! were invented. Check the network / Yahoo and re-run.")
        print("!" * 65)
        print()

    for r in results:
        ticker = r["ticker"]
        if r["status"] == "ok":
            days = r["days_until"]
            urgency = "ACTION REQUIRED" if days <= ALERT_WINDOW else (
                "UPCOMING" if days <= UPCOMING_WINDOW else "on the calendar")
            marker = ">>>" if days <= ALERT_WINDOW else " ! "
            print(f"  [{marker}]  {ticker}  --  {urgency}")
            print(f"         Earnings date : "
                  f"{r['earnings_date'].strftime('%Y-%m-%d')}  ({days} days away)")
        elif r["status"] == "fetch_failed":
            print(f"  [ERR]  {ticker}  --  EARNINGS FETCH FAILED")
            print(f"         yfinance returned no usable data for {ticker}.")
            print(f"         No date invented — check manually.")
        else:
            print(f"  [ ? ]  {ticker}  --  NO EARNINGS DATE FOUND")
            print(f"         yfinance returned no upcoming earnings date for {ticker}.")
            print(f"         Action: Check {ticker} investor relations page manually.")
        if r["milestones"]:
            print(f"         Milestones on file ({len(r['milestones'])}):")
            for m in r["milestones"]:
                if isinstance(m, dict):
                    print(f"           - {m.get('date', 'no date')}: "
                          f"{m.get('milestone', m)}"
                          + (f" — {m['detail']}" if m.get("detail") else ""))
                else:
                    print(f"           - {m}")
        else:
            print(f"         Milestones: none on file "
                  f"(add hand-entered items to data/milestones.json).")
        print()
        print_divider()
        print()

    n_ok = sum(1 for r in results if r["status"] == "ok")
    n_none = sum(1 for r in results if r["status"] == "no_date")
    n_with_milestones = sum(1 for r in results if r["milestones"])
    print_divider("=")
    print(f"  SUMMARY  |  {datetime.today().strftime('%Y-%m-%d %H:%M')}")
    print(f"  Earnings date found : {n_ok}")
    print(f"  No date found       : {n_none}")
    print(f"  Fetch failed        : {n_failed}")
    print(f"  Tickers with milestones on file: {n_with_milestones}")
    print_divider("=")
    print()


if __name__ == "__main__":
    main()
