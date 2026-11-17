"""
Quantum Picks & Shovels — Allocator & Technical Filter
Second Layer Capital

Modeled on the nuclear screener's allocator.py: reads scorer output,
applies a score gate, allocates equal weights across passing names within
a capital budget, and applies the technical filter (above 50-day SMA
required for EXECUTE BUY; RSI >= 70 -> HOLD/overbought; RSI <= 35 with
price above the SMA -> dip alert).

Run from the repo root:

    python allocator.py

You place the orders manually. Only EXECUTE BUY / BUY ALERT (Dip) names
get shares; WAIT / HOLD / DATA ERROR names are listed with 0 shares and
their slice of the budget stays as cash.

OPEN CALLS FOR KEVIN (values below are placeholders, not decisions):
  - SCORE_GATE = 50.0: same gate as the nuclear allocator. Quantum names
    are earlier-stage and mostly pre-revenue, so a lower gate may fit --
    Kevin's call.
  - TOTAL_CAPITAL = $10,000: same budget as the nuclear allocator.
    Kevin's call.
  - Runway exclusion: any ticker the scorer flags with a runway flag
    (any flag containing "runway", e.g. a <12-month cash-runway flag)
    is never allocated, however high it scores. The exact flag string
    depends on the scorer's wording; the substring match is deliberate
    so a rename does not silently re-admit a name.
"""

from data.fetch_fundamentals import (
    fetch_momentum_drawdown,
    fetch_technical_signals,
    load_fundamentals,
)

try:
    from config.universe import QUANTUM_UNIVERSE, YFINANCE_SYMBOLS
except ImportError:  # running from a different cwd
    try:
        from universe import QUANTUM_UNIVERSE
        YFINANCE_SYMBOLS = {}
    except ImportError:
        QUANTUM_UNIVERSE = {}
        YFINANCE_SYMBOLS = {}

SCORE_GATE = 50.0
TOTAL_CAPITAL = 10000.0
LIMIT_OFFSET = 0.005  # limit +0.5% above prior close, house standard


def _is_runway_flagged(item: dict) -> bool:
    """True when the scorer flagged this ticker's cash runway.

    Matches any flag containing "runway" (case-insensitive) so the
    exclusion survives a flag rename; e.g. "RUNWAY_LT_12M",
    "cash_runway_lt_12m", "LOW_RUNWAY".
    """
    flags = item.get("flags") or []
    return any("runway" in str(f).lower() for f in flags)


def _action_for(tech: dict) -> str:
    """Technical-filter action label, mirroring nuclear's allocator."""
    price = tech.get("close_price")
    rsi = tech.get("rsi_14")
    above_sma = tech.get("above_50_sma")
    if price is None:
        return "DATA ERROR"
    if rsi is not None:
        if rsi >= 70.0:
            return "HOLD (Overbought)"
        if rsi <= 35.0 and above_sma:
            return "BUY ALERT (Dip)"
        if above_sma:
            return "EXECUTE BUY"
        return "WAIT (No Trend)"
    return "DATA ERROR"


def build_order_sheet(scores, total_capital=TOTAL_CAPITAL, gate=SCORE_GATE,
                      tech_fn=None, mom_fn=None):
    """Build (and print) the order sheet from scorer output.

    `scores` is the scorer's list of dicts (ticker, name, layer,
    final_score, signal, bucket_count, buckets_possible, flags, factors).
    tech_fn / mom_fn are injectable for testing; they default to the
    live yfinance fetchers. Returns (orders, total_deployed,
    cash_remaining). Orders carry: ticker, score, buckets, momentum,
    drawdown, close, limit_price, shares, cost, action.
    """
    if tech_fn is None:
        tech_fn = fetch_technical_signals
    if mom_fn is None:
        mom_fn = fetch_momentum_drawdown

    passing = [
        s for s in scores
        if s.get("final_score") is not None
        and s["final_score"] >= gate
        and not _is_runway_flagged(s)
    ]
    excluded_runway = [s["ticker"] for s in scores if _is_runway_flagged(s)]

    print("Gathering live calculations from Quantum Engine...")
    if excluded_runway:
        print(f"Runway exclusion (<12M cash runway): "
              f"{', '.join(excluded_runway)} -- never allocated.")
    if not passing:
        print("No companies passed the minimum quality score threshold.")
        return [], 0.0, round(total_capital, 2)

    per_name_budget = total_capital / len(passing)

    print()
    print("=" * 108)
    print("         SECOND LAYER CAPITAL — QUANTUM ALLOCATION & TECHNICAL FILTER")
    print(f"         TOTAL CASH BUDGET: ${total_capital:,.2f}  |  SCORE GATE >= {gate}  "
          f"|  EQUAL WEIGHT ${per_name_budget:,.2f}/NAME")
    print("=" * 108)
    print(f"{'TICKER':<8}{'SCORE':<7}{'BKTS':<6}{'MOM%':<8}{'DD%':<8}"
          f"{'CLOSE':<9}{'LIMIT':<9}{'SHARES':<8}{'COST':<11}{'ACTION'}")
    print("-" * 108)

    orders = []
    total_deployed = 0.0
    for item in passing:
        ticker = item["ticker"]
        score = item["final_score"]
        coverage = f"{item.get('bucket_count')}/{item.get('buckets_possible')}"

        tech = tech_fn(ticker)
        price = tech.get("close_price")
        rsi = tech.get("rsi_14")
        above_sma = tech.get("above_50_sma")
        momentum, drawdown = mom_fn(ticker)

        if price is None:
            print(f"{ticker:<8}{score:<7}{coverage:<6}DATA ERROR — no price data, skipped")
            orders.append({
                "ticker": ticker, "score": score, "buckets": coverage,
                "momentum": momentum, "drawdown": drawdown,
                "close": None, "limit_price": None, "shares": 0,
                "cost": 0.0, "action": "DATA ERROR",
            })
            continue

        action = _action_for(tech)
        limit_price = round(price * (1 + LIMIT_OFFSET), 2)

        # Only actionable names get shares. A name that cannot afford one
        # whole share at its limit price gets 0 shares.
        if action in ("EXECUTE BUY", "BUY ALERT (Dip)"):
            shares = int(per_name_budget / limit_price)
        else:
            shares = 0
        cost = round(shares * limit_price, 2)
        total_deployed += cost

        mom_str = f"{momentum * 100:.1f}%" if momentum is not None else "--"
        dd_str = f"{drawdown * 100:.1f}%" if drawdown is not None else "--"
        rsi_note = ""
        if rsi is not None and action == "HOLD (Overbought)":
            rsi_note = f" (RSI {rsi:.0f})"
        elif rsi is not None and action == "BUY ALERT (Dip)":
            rsi_note = f" (RSI {rsi:.0f})"

        print(f"{ticker:<8}{score:<7}{coverage:<6}{mom_str:<8}{dd_str:<8}"
              f"${price:<8.2f}${limit_price:<8.2f}{shares:<8}${cost:<10.2f}"
              f"{action}{rsi_note}")
        orders.append({
            "ticker": ticker, "score": score, "buckets": coverage,
            "momentum": momentum, "drawdown": drawdown,
            "close": price, "limit_price": limit_price, "shares": shares,
            "cost": cost, "action": action,
        })

    cash_remaining = round(total_capital - total_deployed, 2)
    print("-" * 108)
    print(f"  Total deployed : ${total_deployed:,.2f}")
    print(f"  Cash remaining : ${cash_remaining:,.2f}")
    print("=" * 108)
    return orders, round(total_deployed, 2), cash_remaining


def generate_order_sheet(total_capital=TOTAL_CAPITAL, gate=SCORE_GATE):
    try:
        from scoring.quantum_scorer import calculate_scores
    except ImportError as e:
        print(f"[ERROR] scoring/quantum_scorer.py not available ({e}). "
              f"Allocator needs the scorer; nothing allocated.")
        return [], 0.0, round(total_capital, 2)

    tickers = list(QUANTUM_UNIVERSE)
    fundamentals = load_fundamentals(tickers)
    scores = calculate_scores(fundamentals)
    return build_order_sheet(scores, total_capital=total_capital, gate=gate)


if __name__ == "__main__":
    generate_order_sheet()
