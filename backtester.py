"""
Quantum Picks & Shovels Screener — Backtester
Second Layer Capital

Modeled on the nuclear screener's backtester (same house pattern), with
the two traps from the nuclear backtester audit
(goals/claude-to-muse-transfer-of-automated-investing-projects/files/
nuclear-backtester-audit.md) built out from the start:

  Trap 1 — the "buy and hold benchmark" that was actually daily-
  rebalanced equal weight. This module has TWO benchmarks, honestly
  labeled: build_benchmark_buy_and_hold() (fixed shares, weights
  drift — a real buy-and-hold) and build_benchmark_equal_weight()
  (daily-rebalanced, kept so the difference is visible).
  Trap 2 — the NQS lookahead gate (today's scores gating trades back
  to 2022). The honest (ungated) run uses NO scores at all. A gated
  variant exists only as a diagnostic: it is labeled "(in-sample)" in
  every output line and the report states the gate is lookahead.

Architecture:
  Layer 1 — Price Data      : yfinance daily adjusted close, universe
                               tickers + SGOV. Tickers that return no
                               price history at all (e.g. a bogus
                               ticker in the universe) are dropped
                               with a warning, never fabricated.
  Layer 2 — Signals         : window ROC momentum + rolling-peak
                               drawdown (vectorized, causal).
  Layer 3 — Score Filter    : Optional quality gate on TODAY's
                               quantum final_score (>= 40). Null score
                               passes on price signals alone. A gated
                               run is IN-SAMPLE (lookahead) — see above.
  Layer 4 — Position Logic  : Equal-weight qualifying assets, 0.05%
                               slippage on rebalance days, SGOV when
                               nothing qualifies.
  Layer 5 — Metrics         : Total return, annualized vol, Sharpe,
                               max drawdown. Both benchmarks aligned
                               to the same trading days as the strategy.

Momentum windows: 14 / 60 / 200 days (same as nuclear — same house
windows, so the two screeners stay comparable; no change justified).
Risk controls: 15% trailing drawdown stop, 100% take-profit, 0.05%
slippage. Defensive asset: SGOV.

Standing limitations (cannot be fixed from inside this repo):
  - Survivorship: today's universe is run back to START_DATE. Any
    quantum name that failed or delisted in that span never appears.
  - No IPO floors: unlike nuclear (OKLO/GEV/TLN SPAC floors), no
    verified floor dates exist for the quantum names, so none are
    applied. Do NOT invent floor dates — a name whose ticker history
    starts as a SPAC shell would carry that shell history.
  - No equity-curve chart: nuclear writes a PNG; this module prints
    the matrix only (chart file not in scope for this build).

Run window override (for short verification runs):
  QUANTUM_BACKTEST_START / QUANTUM_BACKTEST_END env vars.
"""

import json
import os
import sys
import warnings
from datetime import datetime

import numpy as np
import pandas as pd
import yfinance as yf

warnings.filterwarnings("ignore", category=FutureWarning)

# ── Parameters ────────────────────────────────────────────────────────────────

DEFENSIVE_ASSET = "SGOV"
START_DATE = os.environ.get("QUANTUM_BACKTEST_START", "2022-01-01")
END_DATE = os.environ.get("QUANTUM_BACKTEST_END", datetime.today().strftime("%Y-%m-%d"))

MOMENTUM_WINDOWS = [14, 60, 200]
DRAWDOWN_LIMIT = 0.15
TAKE_PROFIT = 1.00
SLIPPAGE = 0.0005
RISK_FREE_RATE = 0.05
SCORE_MIN_THRESHOLD = 40  # House backtester threshold (nuclear uses 40).
# NOTE: the nuclear allocator uses 50 and live_signal uses 40 — which
# number is the house standard is still Kevin's call. This module
# follows the backtester (40) for comparability.

DATA_STORAGE_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data_storage")

# Yahoo Finance symbol overrides (ASMI delisted from Nasdaq; its live
# listing is Euronext ASM.AS). load_prices downloads the mapped symbol
# and renames the column back to the universe ticker, so the rest of
# the backtester never sees the override.
try:
    from config.universe import YFINANCE_SYMBOLS
except ImportError:  # running from a different cwd
    try:
        from universe import YFINANCE_SYMBOLS
    except ImportError:
        YFINANCE_SYMBOLS = {}


# ── Universe ──────────────────────────────────────────────────────────────────

def load_universe():
    """Return (tickers, meta) from the universe registry.

    Prefers config/universe.py if it exists (the overhaul layout),
    falls back to the root universe.py. Handles a flat
    {ticker: meta} dict, a nuclear-style nested {domain: {tickers:
    [...]}} dict, or a plain ticker list. Tickers are never hardcoded
    here — the registry is the single source of truth.
    """
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
            "universe.py could be imported. Refusing to backtest "
            "on a guessed ticker list."
        )

    if isinstance(raw, (list, tuple)):
        return list(raw), {t: {} for t in raw}

    if isinstance(raw, dict):
        # Nuclear-style nested {domain: {"tickers": [...]}} ?
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
        # Flat {ticker: meta} (quantum root universe.py).
        return list(raw.keys()), dict(raw)

    raise RuntimeError(f"Universe registry has an unrecognized shape: {type(raw)}")


# ── Layer 1: Price Data ───────────────────────────────────────────────────────

def load_prices(tickers=None):
    """Download adjusted closes for the universe + SGOV.

    Tickers that return no price history at all are dropped with a
    warning — a bogus ticker must never be filled with invented
    prices, and it must not crash the run for the other names.
    """
    if tickers is None:
        tickers, _ = load_universe()
    all_tickers = list(tickers) + [DEFENSIVE_ASSET]
    print(f"[DATA] Downloading price history for {len(all_tickers)} tickers "
          f"({START_DATE} → {END_DATE})...")

    yf_tickers = [YFINANCE_SYMBOLS.get(t, t) for t in all_tickers]
    raw = yf.download(yf_tickers, start=START_DATE, end=END_DATE,
                      auto_adjust=True, progress=False)["Close"]
    if isinstance(raw, pd.Series):
        raw = raw.to_frame()
    # Rename mapped symbols (e.g. ASM.AS) back to universe tickers (ASMI).
    raw = raw.rename(columns={YFINANCE_SYMBOLS.get(t, t): t
                              for t in all_tickers})
    raw = raw.ffill()
    raw = raw.dropna(how="all")

    # Drop tickers with no usable history (never fabricate).
    dropped = [t for t in all_tickers if t not in raw.columns
               or raw[t].dropna().empty]
    for t in dropped:
        print(f"[DATA] WARNING: {t} returned no price history — "
              f"dropped from this run (no data invented).")
    kept = [t for t in tickers if t not in dropped]
    if not kept:
        raise RuntimeError("No universe ticker returned price history.")
    if DEFENSIVE_ASSET in dropped:
        raise RuntimeError("Defensive asset SGOV returned no price history.")

    equity_prices = raw[kept]
    defensive_prices = raw[DEFENSIVE_ASSET]

    print(f"[DATA] Loaded {len(raw)} trading days. "
          f"Earliest: {raw.index[0].date()}, Latest: {raw.index[-1].date()}")
    for t in kept:
        first_valid = equity_prices[t].first_valid_index()
        if first_valid and first_valid > raw.index[0]:
            print(f"[DATA] {t}: history starts {first_valid.date()}")

    return equity_prices, defensive_prices


# ── Layer 2: Signals ──────────────────────────────────────────────────────────

def build_signals(equity_prices: pd.DataFrame, window: int):
    momentum_scores = equity_prices.pct_change(periods=window)
    rolling_peaks = equity_prices.cummax()
    asset_drawdowns = (equity_prices - rolling_peaks) / rolling_peaks
    return momentum_scores, asset_drawdowns


# ── Layer 3: Score Filter ─────────────────────────────────────────────────────

def _load_fundamentals(tickers):
    """Hand the scorer its fundamentals dict: {ticker: dict | None}.

    Reads the SEC-cache JSONs in data_storage/ when present (the old
    ingestion pipeline's output). A ticker with no cache file gets
    None — the scorer contract allows None, and a missing file is
    reported, never papered over with invented fundamentals.
    """
    fundamentals = {}
    for ticker in tickers:
        path = os.path.join(DATA_STORAGE_DIR, f"{ticker}_data.json")
        if os.path.exists(path):
            try:
                with open(path) as f:
                    fundamentals[ticker] = json.load(f)
            except Exception as e:
                print(f"[SCORE] {ticker}: fundamentals file unreadable "
                      f"({e}) — scored as None.")
                fundamentals[ticker] = None
        else:
            fundamentals[ticker] = None
    missing = [t for t, v in fundamentals.items() if v is None]
    if missing:
        print(f"[SCORE] No fundamentals on file for: {', '.join(missing)} "
              f"(scored as None).")
    return fundamentals


def load_quantum_scores(tickers=None):
    """Load TODAY's quantum final_score for every ticker.

    A total failure — scorer unimportable, or no ticker scores at
    all — raises RuntimeError. The gate must never silently vanish.
    Per-ticker None passes on price signals alone, by design (same
    as nuclear's null-NQS pass). Callers that can proceed without
    the gate (main()) catch this, print a loud banner, and run
    ungated only.
    """
    if tickers is None:
        tickers, _ = load_universe()
    try:
        from scoring.quantum_scorer import calculate_scores
    except Exception as e:
        raise RuntimeError(
            "Quantum score gate unavailable: cannot import "
            f"scoring.quantum_scorer ({e}). Refusing to run a gated "
            "backtest on price signals alone."
        ) from e

    fundamentals = _load_fundamentals(tickers)
    try:
        results = calculate_scores(fundamentals)
    except Exception as e:
        raise RuntimeError(
            f"Quantum score gate unavailable: calculate_scores failed ({e})."
        ) from e

    scores = {}
    for row in results or []:
        scores[row.get("ticker")] = row.get("final_score")
    for ticker in tickers:
        scores.setdefault(ticker, None)

    failures = [t for t, v in scores.items() if v is None]
    for ticker in failures:
        print(f"[SCORE] {ticker}: no score — passes on price signals alone.")
    if all(v is None for v in scores.values()):
        raise RuntimeError(
            "Quantum score gate unavailable: no ticker scored. "
            "Refusing to run a gated backtest on price signals alone."
        )
    return scores


def score_passes(ticker: str, scores: dict) -> bool:
    if scores is None:
        return True  # ungated variant: no score check at all
    score = scores.get(ticker)
    if score is None:
        return True
    return score >= SCORE_MIN_THRESHOLD


# ── Layer 4: Position Construction ────────────────────────────────────────────

def run_backtest(equity_prices, defensive_prices, window, scores=None):
    """Run one momentum variant.

    scores=None means UNGATED (momentum + drawdown only — the honest
    variant). A dict means gated on today's quantum final_score
    (in-sample — see the module docstring; the gate is lookahead,
    not a tradable result). Risk controls: 15% trailing-drawdown
    stop, 100% take-profit, 0.05% slippage on rebalance days.
    Tickers are taken from equity_prices.columns, never hardcoded.
    """
    tickers = list(equity_prices.columns)
    momentum_scores, asset_drawdowns = build_signals(equity_prices, window)
    equity_returns = equity_prices.pct_change()
    defensive_returns = defensive_prices.pct_change()
    trading_days = equity_prices.index[window + 1:]

    strategy_returns = []
    equity_value = 1.0
    equity_curve = [equity_value]
    prev_basket = []
    entry_prices = {t: None for t in tickers}
    trade_log = []

    for i, current_day in enumerate(trading_days):
        signal_day = equity_prices.index[window + i]
        day_momentum = momentum_scores.loc[signal_day]
        day_drawdowns = asset_drawdowns.loc[signal_day]

        basket = []
        for ticker in tickers:
            if pd.isna(day_momentum[ticker]):
                continue
            if day_momentum[ticker] <= 0:
                entry_prices[ticker] = None
                continue
            if day_drawdowns[ticker] <= -DRAWDOWN_LIMIT:
                entry_prices[ticker] = None
                continue
            if entry_prices[ticker] is None:
                entry_prices[ticker] = equity_prices.loc[signal_day, ticker]
            current_gain = (equity_prices.loc[signal_day, ticker] /
                            entry_prices[ticker]) - 1.0
            if current_gain >= TAKE_PROFIT:
                entry_prices[ticker] = None
                trade_log.append({"date": current_day, "ticker": ticker,
                                  "event": "take_profit",
                                  "gain_pct": round(current_gain * 100, 2)})
                continue
            if scores is not None and not score_passes(ticker, scores):
                continue
            basket.append(ticker)

        slippage_drag = SLIPPAGE if basket != prev_basket else 0.0

        if basket:
            weight = 1.0 / len(basket)
            daily_return = (equity_returns.loc[current_day, basket].sum() * weight) - slippage_drag
        else:
            daily_return = defensive_returns.loc[current_day] - slippage_drag
            if prev_basket:
                trade_log.append({"date": current_day, "ticker": "SGOV",
                                  "event": "defensive_rotation", "gain_pct": None})

        strategy_returns.append(daily_return)
        equity_value *= (1 + daily_return)
        equity_curve.append(equity_value)
        prev_basket = basket

    returns_series = pd.Series(strategy_returns, index=trading_days)
    curve_series = pd.Series(equity_curve, index=equity_prices.index[window:])
    return returns_series, curve_series, trade_log


# ── Layer 5: Metrics ──────────────────────────────────────────────────────────

def calc_metrics(returns: pd.Series, label: str) -> dict:
    if returns.empty:
        return {"label": label, "total_return": None, "ann_vol": None,
                "sharpe": None, "max_drawdown": None, "n_days": 0}

    total_return = (1 + returns).prod() - 1
    ann_vol = returns.std() * np.sqrt(252)
    excess = returns - (RISK_FREE_RATE / 252)
    sharpe = (excess.mean() / returns.std() * np.sqrt(252)
              if returns.std() > 0 else None)
    cum = (1 + returns).cumprod()
    rolling_max = cum.cummax()
    max_drawdown = ((cum - rolling_max) / rolling_max).min()

    return {
        "label": label,
        "total_return": round(total_return * 100, 2),
        "ann_vol": round(ann_vol * 100, 2),
        "sharpe": round(sharpe, 3) if sharpe is not None else None,
        "max_drawdown": round(max_drawdown * 100, 2),
        "n_days": len(returns),
    }


def build_benchmark_buy_and_hold(equity_prices, start_idx):
    """TRUE buy-and-hold benchmark: fixed shares, weights drift.

    Equal dollars in each ticker that has a valid price on the start
    day; the share counts then stay fixed, so weights drift with
    prices — that is what buy-and-hold means. A ticker that lists
    later never joins (it did not exist on the start day). Returns
    start on index[start_idx + 1], the same first trading day as a
    strategy with window=start_idx, so the comparison covers
    identical days.
    """
    start_day = equity_prices.index[start_idx]
    start_prices = equity_prices.loc[start_day].dropna()
    if start_prices.empty:
        return pd.Series(dtype=float), pd.Series(dtype=float)

    growth = equity_prices[start_prices.index].div(start_prices).ffill()
    bench_value = growth.mean(axis=1).loc[equity_prices.index[start_idx:]]
    bench_days = equity_prices.index[start_idx + 1:]
    bench_daily = bench_value.pct_change().loc[bench_days].fillna(0.0)
    return bench_daily, bench_value


def build_benchmark_equal_weight(equity_prices, start_idx):
    """Daily-rebalanced equal-weight benchmark (the ORIGINAL nuclear
    benchmark, kept here so the difference is visible).

    Each day the return is the mean daily return of the tickers with
    a valid return that day — i.e. the portfolio is rebalanced back
    to equal weight EVERY day. This is NOT buy-and-hold: weights
    never drift, and a ticker that lists later joins at full equal
    weight the day its first return appears. Returns start on
    index[start_idx + 1], the same first trading day as a strategy
    with window=start_idx.
    """
    returns = equity_prices.pct_change()
    bench_days = equity_prices.index[start_idx + 1:]
    bench_returns_list = []
    prev_count = None
    comp_log = []

    for day in bench_days:
        valid = returns.loc[day].dropna()
        valid_count = len(valid)
        if valid_count == 0:
            bench_returns_list.append(0.0)
            continue
        bench_returns_list.append(valid.sum() * (1.0 / valid_count))
        if valid_count != prev_count:
            comp_log.append(f"[BENCHMARK] {day.date()}: {valid_count} tickers active "
                            f"({', '.join(valid.index.tolist())})")
            prev_count = valid_count

    for entry in comp_log:
        print(entry)

    bench_daily = pd.Series(bench_returns_list, index=bench_days)
    bench_curve = pd.Series([1.0] + list((1 + bench_daily).cumprod()),
                            index=equity_prices.index[start_idx:])
    return bench_daily, bench_curve


# ── Labels & Report ───────────────────────────────────────────────────────────

def strategy_label(window: int, gated: bool) -> str:
    """Label for one momentum variant. The gated variant is always
    marked in-sample: its score gate is today's scores applied to
    the whole history (lookahead), not a tradable result."""
    if gated:
        return f"{window}-Day Momentum + Score gate (in-sample)"
    return f"{window}-Day Momentum"


def print_report(metrics_list, run_info):
    """Print the backtest matrix.

    run_info: {"start_date", "end_date", "data_start", "data_end",
    "score_gate"} — the run window and gate status are part of the
    output so the numbers are reproducible: END_DATE defaults to
    today, so a rerun on another day covers another window.
    """
    print("\n" + "=" * 65)
    print("  SECOND LAYER CAPITAL — QUANTUM BACKTEST MATRIX")
    print(f"  Run window: {run_info['start_date']} → {run_info['end_date']} "
          f"(data: {run_info['data_start']} → {run_info['data_end']})")
    print("  Risk controls: 15% stop-loss | 100% take-profit | 0.05% slippage")
    print(f"  Score gate: {run_info['score_gate']}")
    print("  NOTE: any variant labeled (in-sample) is gated on TODAY's")
    print("  scores applied to the whole history — lookahead, not tradable.")
    print("=" * 65)
    print(f"  {'Strategy':<28} {'Return':>9} {'Ann.Vol':>9} {'Sharpe':>8} {'MaxDD':>9}")
    print("  " + "-" * 63)
    for m in metrics_list:
        if m["total_return"] is None:
            continue
        print(f"  {m['label']:<28} "
              f"{m['total_return']:>8.1f}% "
              f"{m['ann_vol']:>8.1f}% "
              f"{str(m['sharpe']):>8} "
              f"{m['max_drawdown']:>8.1f}%")
    print("=" * 65 + "\n")


# ── Main ──────────────────────────────────────────────────────────────────────

def _run_one_variant(equity_prices, defensive_prices, window, label, scores,
                     all_metrics):
    print(f"\n[BACKTEST] Running {label}...")
    returns, curve, trade_log = run_backtest(
        equity_prices, defensive_prices, window, scores)
    metrics = calc_metrics(returns, label)
    all_metrics.append(metrics)
    tp_events = [e for e in trade_log if e["event"] == "take_profit"]
    def_events = [e for e in trade_log if e["event"] == "defensive_rotation"]
    print(f"[BACKTEST] {label}: {metrics['total_return']}% total | "
          f"{metrics['ann_vol']}% vol | Sharpe {metrics['sharpe']} | "
          f"MaxDD {metrics['max_drawdown']}% | "
          f"{len(tp_events)} take-profits | {len(def_events)} defensive rotations")


def main():
    tickers, _meta = load_universe()
    print(f"[UNIVERSE] {len(tickers)} tickers: {', '.join(tickers)}")
    equity_prices, defensive_prices = load_prices(tickers)
    data_start = equity_prices.index[0].date()
    data_end = equity_prices.index[-1].date()

    # Scores are needed only for the gated (in-sample) variants. A
    # total load failure must not silently turn the gate off: banner
    # loudly, skip the gated variants, record it in the report. The
    # ungated (honest) variants and benchmarks still run, and the
    # exit code stays 0 — the gate is a diagnostic here, and the
    # scorer is still being built by a sibling workstream.
    scores = None
    score_gate = ""
    print("[SCORE] Loading quantum final_scores...")
    try:
        scores = load_quantum_scores(list(equity_prices.columns))
    except RuntimeError as e:
        print("!" * 65)
        print(f"!!! SCORE GATE OFF: {e}")
        print("!!! Gated variants skipped — ungated momentum and benchmarks still run.")
        print("!" * 65)
        score_gate = f"OFF — load failed ({e}); gated variants skipped"
    if scores is not None:
        scored = {t: v for t, v in scores.items() if v is not None}
        print("[SCORE] Scored tickers: " + ", ".join(f"{t}={v}" for t, v in scored.items()))
        null_count = len(scores) - len(scored)
        score_gate = (f"ACTIVE ({len(scored)}/{len(scores)} scored, "
                      f"threshold {SCORE_MIN_THRESHOLD}) — IN-SAMPLE / LOOKAHEAD")
        if null_count:
            score_gate += f" — {null_count} null, passing on price signals"

    all_metrics = []

    for window in MOMENTUM_WINDOWS:
        # Ungated momentum: the honest variant (no lookahead gate).
        _run_one_variant(equity_prices, defensive_prices, window,
                         strategy_label(window, gated=False), None,
                         all_metrics)
        # Gated momentum: today's scores applied to the whole history —
        # in-sample, labeled as such.
        if scores is not None:
            _run_one_variant(equity_prices, defensive_prices, window,
                             strategy_label(window, gated=True), scores,
                             all_metrics)

        # Benchmarks over the SAME trading days as this window's
        # strategies, so the comparison covers identical days.
        print(f"\n[BACKTEST] Building benchmarks for {window}-day window...")
        bh_returns, _bh_curve = build_benchmark_buy_and_hold(equity_prices, window)
        bh_label = f"Benchmark (Buy & Hold) — {window}D"
        bh_metrics = calc_metrics(bh_returns, bh_label)
        all_metrics.append(bh_metrics)
        print(f"[BACKTEST] {bh_label}: {bh_metrics['total_return']}% total | "
              f"Sharpe {bh_metrics['sharpe']} | MaxDD {bh_metrics['max_drawdown']}%")

        ew_returns, _ew_curve = build_benchmark_equal_weight(equity_prices, window)
        ew_label = f"Equal-Weight (daily rebalanced) — {window}D"
        ew_metrics = calc_metrics(ew_returns, ew_label)
        all_metrics.append(ew_metrics)
        print(f"[BACKTEST] {ew_label}: {ew_metrics['total_return']}% total | "
              f"Sharpe {ew_metrics['sharpe']} | MaxDD {ew_metrics['max_drawdown']}%")

    run_info = {"start_date": START_DATE, "end_date": END_DATE,
                "data_start": str(data_start), "data_end": str(data_end),
                "score_gate": score_gate}
    print_report(all_metrics, run_info)

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
