"""
Quantum composite scorer (0-100), house pattern per scoring/nqs_scorer.py
in the nuclear screener: missing data = factor EXCLUDED from the average
with remaining weights renormalized, never scored zero; bucket counts /
coverage printed next to every score so a thin-evidence score cannot be
mistaken for a well-covered one.

Factors (six, each scored 0-100 with documented caps):
  rd_intensity      R&D expense / revenue; for pre-revenue names, R&D /
                    annual burn (share of burn that is R&D — thesis
                    Section 3.1: scale R&D against absolute cash burn).
  cash_runway       Total cash / annual burn, in years. Cash-flow-positive
                    (burn <= 0) scores 100. Runway < 12 months flags
                    "RUNWAY < 12M" and caps the signal at WEAK.
  revenue_growth    YoY revenue growth (decimal). MISSING for pre-revenue
                    names — never a made-up default. (The old scoring.py
                    defaulted this to 0.20; that is the bug being fixed.)
  gross_margin_level  Gross margin LEVEL (gross profit / revenue), never a
                    trend. MISSING for pre-revenue names.
  dilution          Share-count growth YoY (decimal). High dilution lowers
                    the score; buyback / flat counts score 100.
  thesis_milestone  Manual 0-100 input per ticker (engineering milestones,
                    contract wins, etc.). Default None = missing, NEVER
                    invented. No source for this exists yet — see open
                    calls at the bottom of this docstring.

Weights — KEVIN'S OPEN CALL, not settled. Two sets, one per group:
  Pure-plays (HARDWARE_MODALITY — pre-revenue, thesis-driven):
      rd_intensity 0.30, cash_runway 0.30, revenue_growth 0.10,
      gross_margin_level 0.05, dilution 0.10, thesis_milestone 0.15
  Enablers (CONTROL_SYSTEMS_RF, CRYOGENICS_ENVIRONMENT,
  UPSTREAM_MATERIALS — profitable large-caps):
      rd_intensity 0.15, cash_runway 0.20, revenue_growth 0.20,
      gross_margin_level 0.20, dilution 0.10, thesis_milestone 0.15
  Both sum to 1.0. Rationale: for pure-plays survival (runway) and R&D
  commitment are the thesis; growth/margin usually do not exist yet, so
  they carry little weight. For enablers, growth and margin level are
  real, comparable numbers and carry real weight. Dilution and the
  manual thesis bucket are weighted the same in both groups.

Signals (house thresholds): STRONG >= 75, NEUTRAL 50-74, WEAK 25-49,
CRITICAL < 25. A ticker with no fundamentals at all scores None / "NO DATA".

Accepted fundamentals keys per ticker (all optional; absent = missing):
  revenue, research_and_development, gross_profit, gross_margin,
  total_cash, annual_burn_rate, revenue_growth, share_count_growth,
  thesis_score. Aliases: rd_expense, burn_rate, shares_outstanding_growth.

No fabricated / mock / fallback data anywhere in this module. No Streamlit.

Open calls for Kevin:
  1. The two weight sets above (pure-play vs enabler) — approve or change.
  2. Where thesis_milestone scores come from (manual overrides file?
     conference intel? insider signal?) and who maintains them.
  3. Whether the RUNWAY < 12M signal cap (WEAK at best) should also
     block a ticker from the allocator entirely, as the nuclear screener
     does with its gates.
  4. Whether enablers with negative EBITDA / negative operating cash
     flow should score 0 on runway (known-bad, as nuclear does) rather
     than None — currently burn <= 0 scores 100, which treats a
     loss-making enabler the same as a profitable one if burn is
     derived from net income. The burn input needs a definition.

Run from the repo root (`python -m scoring.quantum_scorer`). Running the
file directly fails on the absolute imports below — that is standard
Python layout, not a bug.
"""

import json
import math
import os

from config.universe import QUANTUM_UNIVERSE, get_layer_for_ticker

# -- Signal thresholds (house standard) ---------------------------------------
STRONG_MIN = 75
NEUTRAL_MIN = 50
WEAK_MIN = 25

RUNWAY_FLAG_MONTHS = 12  # under 12 months: flag + signal capped at WEAK

# -- Factor weights per group (Kevin's open call — see module docstring) ------
WEIGHTS = {
    "pure_play": {
        "rd_intensity": 0.30,
        "cash_runway": 0.30,
        "revenue_growth": 0.10,
        "gross_margin_level": 0.05,
        "dilution": 0.10,
        "thesis_milestone": 0.15,
    },
    "enabler": {
        "rd_intensity": 0.15,
        "cash_runway": 0.20,
        "revenue_growth": 0.20,
        "gross_margin_level": 0.20,
        "dilution": 0.10,
        "thesis_milestone": 0.15,
    },
}

# Factors that are structurally not applicable to a known pre-revenue ticker.
PRE_REVENUE_EXCLUDED_FACTORS = ("revenue_growth", "gross_margin_level")

FACTOR_KEYS = (
    "rd_intensity",
    "cash_runway",
    "revenue_growth",
    "gross_margin_level",
    "dilution",
    "thesis_milestone",
)


def _present(value) -> bool:
    """True when a value is usable: not None and not NaN."""
    return value is not None and not (isinstance(value, float) and math.isnan(value))


def _num(value):
    """Coerce to float, or None if missing / non-numeric / NaN / infinite."""
    if not _present(value):
        return None
    try:
        out = float(value)
    except (TypeError, ValueError):
        return None
    if math.isnan(out) or math.isinf(out):
        return None
    return out


def _first_present(data: dict, *keys):
    """First usable numeric value under any of the given keys, else None."""
    for key in keys:
        value = _num(data.get(key))
        if value is not None:
            return value
    return None


def _ladder(value: float, tiers) -> float:
    """First tier whose floor the value meets, else the final fallback.

    tiers: list of (floor, score) in descending floor order, ending with
    a (-inf, score) catch-all. Every ladder in this module ends that way,
    so no input falls through unscored.
    """
    for floor, score in tiers:
        if value >= floor:
            return float(score)
    return float(tiers[-1][1])


# -- Per-factor sub-scorers (each returns 0-100 float or None) ----------------

def score_rd_intensity(data: dict, revenue, burn_rate):
    """R&D / revenue; pre-revenue names use R&D / annual burn instead.

    Ladder (same for both paths — it is a share, not a dollar amount):
    >= 0.50 -> 100, >= 0.30 -> 85, >= 0.15 -> 65, >= 0.05 -> 45,
    > 0 -> 25, 0 -> 0. Negative R&D is invalid input -> None.
    Returns None when neither ratio can be computed (no divide by zero:
    revenue and burn are both guarded before any division).
    """
    rd = _first_present(data, "research_and_development", "rd_expense",
                        "research_and_development_expense")
    if rd is None or rd < 0:
        return None
    ratio = None
    if revenue is not None and revenue > 0:
        ratio = rd / revenue
    elif burn_rate is not None and burn_rate > 0:
        ratio = rd / burn_rate
    if ratio is None:
        return None
    return _ladder(ratio, [
        (0.50, 100), (0.30, 85), (0.15, 65), (0.05, 45),
        (0.0, 25), (float("-inf"), 0),
    ]) if ratio > 0 else 0.0


def score_cash_runway(data: dict):
    """Cash runway in years, from total_cash / annual_burn_rate.

    Returns (sub_score or None, runway_years or None). Burn <= 0 means
    cash-flow-positive (or breakeven): scores 100, runway is None because
    there is no burn to divide by — and no division is attempted.
    Missing cash with positive burn, or missing burn, -> (None, None).
    """
    burn = _first_present(data, "annual_burn_rate", "burn_rate",
                          "annual_cash_burn")
    cash = _num(data.get("total_cash"))
    if burn is None:
        return None, None
    if burn <= 0:
        return 100.0, None
    if cash is None:
        return None, None
    years = max(cash, 0.0) / burn  # burn > 0 here; cash floored at 0
    return _ladder(years, [
        (5.0, 100), (3.0, 85), (2.0, 70), (1.5, 55), (1.0, 40),
        (0.5, 20), (float("-inf"), 5),
    ]), years


def score_revenue_growth(data: dict, is_pre_revenue: bool):
    """YoY revenue growth. None for pre-revenue names (hard rule) and
    None when the input is absent — never a made-up default."""
    if is_pre_revenue:
        return None
    growth = _num(data.get("revenue_growth"))
    if growth is None:
        return None
    return _ladder(growth, [
        (0.30, 100), (0.20, 85), (0.10, 70), (0.05, 55), (0.0, 40),
        (-0.10, 20), (float("-inf"), 5),
    ])


def score_gross_margin_level(data: dict, revenue, is_pre_revenue: bool):
    """Gross margin LEVEL (not a trend). None for pre-revenue names and
    None when neither a direct gross_margin nor gross_profit/revenue is
    available. A known negative margin scores 5 (known-bad, not missing).
    """
    if is_pre_revenue:
        return None
    margin = _num(data.get("gross_margin"))
    if margin is None:
        gross_profit = _num(data.get("gross_profit"))
        if gross_profit is None or revenue is None or revenue <= 0:
            return None
        margin = gross_profit / revenue
    return _ladder(margin, [
        (0.60, 100), (0.45, 85), (0.30, 70), (0.15, 50), (0.0, 30),
        (float("-inf"), 5),
    ])


def score_dilution(data: dict):
    """Share-count growth YoY, inverted: low dilution scores high.
    <= 0 (buyback/flat) -> 100, <= 0.02 -> 85, <= 0.05 -> 70,
    <= 0.10 -> 50, <= 0.20 -> 30, > 0.20 -> 10. None when absent."""
    growth = _first_present(data, "share_count_growth",
                            "shares_outstanding_growth",
                            "share_count_growth_yoy", "dilution")
    if growth is None:
        return None
    return _dilution_ladder(growth)


def _dilution_ladder(growth: float) -> float:
    # Inverted ladder: lower growth is better, so floors run high-to-low
    # and the first tier the value is AT OR BELOW wins.
    if growth <= 0:
        return 100.0
    if growth <= 0.02:
        return 85.0
    if growth <= 0.05:
        return 70.0
    if growth <= 0.10:
        return 50.0
    if growth <= 0.20:
        return 30.0
    return 10.0


def score_thesis_milestone(data: dict):
    """Manual 0-100 thesis/milestone input. None when absent — never
    invented. Out-of-range values are clamped to [0, 100]."""
    value = _num(data.get("thesis_score"))
    if value is None:
        return None
    return float(min(max(value, 0.0), 100.0))


# -- Composite -----------------------------------------------------------------

def _signal_for(score, runway_flag: bool) -> str:
    if score is None:
        return "NO DATA"
    if score >= STRONG_MIN:
        signal = "STRONG"
    elif score >= NEUTRAL_MIN:
        signal = "NEUTRAL"
    elif score >= WEAK_MIN:
        signal = "WEAK"
    else:
        signal = "CRITICAL"
    if runway_flag and signal in ("STRONG", "NEUTRAL"):
        signal = "WEAK"  # runway < 12M caps the signal at WEAK at best
    return signal


def calculate_scores(fundamentals: dict) -> list:
    """Score every universe ticker against its fundamentals dict.

    fundamentals: {ticker: dict | None}. A ticker with no fundamentals at
    all scores None / "NO DATA". Returns one dict per universe ticker,
    sorted by final_score descending (None last), each with keys:
    ticker, name, layer, final_score, signal, bucket_count,
    buckets_possible, flags, factors.
    """
    results = []
    for ticker, meta in QUANTUM_UNIVERSE.items():
        layer = meta["layer"]
        group = "pure_play" if layer == "HARDWARE_MODALITY" else "enabler"
        weights = WEIGHTS[group]
        data = fundamentals.get(ticker) if fundamentals else None

        flags = []
        factors = {key: None for key in FACTOR_KEYS}
        runway_years = None

        if data is None:
            results.append({
                "ticker": ticker,
                "name": meta["name"],
                "layer": layer,
                "final_score": None,
                "signal": "NO DATA",
                "bucket_count": 0,
                "buckets_possible": len(FACTOR_KEYS),
                "flags": flags,
                "factors": factors,
            })
            continue

        revenue = _num(data.get("revenue"))
        # Known zero (or negative — invalid, treated as zero) revenue:
        # pre-revenue rule applies. Revenue None means unknown, not
        # pre-revenue — growth/margin are then missing, not excluded.
        is_pre_revenue = revenue is not None and revenue <= 0
        if is_pre_revenue:
            flags.append("PRE-REVENUE")

        burn = _first_present(data, "annual_burn_rate", "burn_rate",
                              "annual_cash_burn")

        factors["rd_intensity"] = score_rd_intensity(data, revenue, burn)
        factors["cash_runway"], runway_years = score_cash_runway(data)
        factors["revenue_growth"] = score_revenue_growth(data, is_pre_revenue)
        factors["gross_margin_level"] = score_gross_margin_level(
            data, revenue, is_pre_revenue)
        factors["dilution"] = score_dilution(data)
        factors["thesis_milestone"] = score_thesis_milestone(data)

        runway_flag = (
            runway_years is not None and runway_years * 12 < RUNWAY_FLAG_MONTHS
        )
        if runway_flag:
            flags.append("RUNWAY < 12M")

        dilution_growth = _first_present(
            data, "share_count_growth", "shares_outstanding_growth",
            "share_count_growth_yoy", "dilution")
        if dilution_growth is not None and dilution_growth > 0.20:
            flags.append("HIGH DILUTION >20%/YR")

        # Buckets that could apply: growth + margin are structurally
        # excluded for a known pre-revenue ticker; everything else counts.
        buckets_possible = len(FACTOR_KEYS)
        if is_pre_revenue:
            buckets_possible -= len(PRE_REVENUE_EXCLUDED_FACTORS)

        scored = {k: v for k, v in factors.items() if v is not None}
        if scored:
            weight_sum = sum(weights[k] for k in scored)
            final_score = round(
                sum(weights[k] * v for k, v in scored.items()) / weight_sum, 1)
        else:
            final_score = None

        results.append({
            "ticker": ticker,
            "name": meta["name"],
            "layer": layer,
            "final_score": final_score,
            "signal": _signal_for(final_score, runway_flag),
            "bucket_count": len(scored),
            "buckets_possible": buckets_possible,
            "flags": flags,
            "factors": factors,
        })

    return sorted(results, key=lambda r: (r["final_score"] is None,
                                          -(r["final_score"] or 0)))


# -- Data loading / display ----------------------------------------------------

def load_fundamentals(data_folder) -> dict:
    """Load {TICKER}_data.json per universe ticker from data_folder.

    Missing file -> None for that ticker (no fallback data, no invented
    values). Missing folder -> all None. Returns {ticker: dict | None}.
    """
    fundamentals = {}
    for ticker in QUANTUM_UNIVERSE:
        path = os.path.join(str(data_folder), f"{ticker}_data.json")
        if not os.path.exists(path):
            fundamentals[ticker] = None
            continue
        with open(path, "r") as f:
            fundamentals[ticker] = json.load(f)
    return fundamentals


def print_results_table(rankings: list) -> None:
    """Shared results table printer (also used by __main__)."""
    print(f"\n{'TICKER':<8}{'LAYER':<24}{'SCORE':<8}{'BKTS':<7}{'SIGNAL':<9}{'FLAGS'}")
    print("-" * 90)
    for r in rankings:
        score = r["final_score"] if r["final_score"] is not None else "N/A"
        coverage = f"{r['bucket_count']}/{r['buckets_possible']}"
        flags = ", ".join(r["flags"]) if r["flags"] else "-"
        print(f"{r['ticker']:<8}{r['layer']:<24}{str(score):<8}"
              f"{coverage:<7}{r['signal']:<9}{flags}")
    print()


if __name__ == "__main__":
    data_folder = os.path.join(os.path.dirname(__file__), "..", "data_storage")
    if not os.path.isdir(data_folder):
        print(f"[!] No data folder found at {data_folder} — "
              "all tickers will show NO DATA.")
    print_results_table(calculate_scores(load_fundamentals(data_folder)))
