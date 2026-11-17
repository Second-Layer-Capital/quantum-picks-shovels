# Second Layer Capital — Quantum Picks & Shovels Screener

A systematic, quantitative "picks-and-shovels" investment framework and stock evaluation engine targeting critical supply chain bottlenecks across the quantum computing industrial complex. Terminal-only: no dashboard, no web UI. Run everything from the repo root.

The strategy thesis lives in `INVESTMENT_THESIS.md`. Note: the thesis and `OPERATIONS_PLAYBOOK.md` were not rewritten in the 2026-11-16 overhaul and still describe deleted modules — see `docs/DECISIONS.md` for the contradictions.

## 🗺️ Strategy Architecture

9 tickers across 4 layers (`config/universe.py`), plus an empty watchlist (no additional candidates could be verified from the thesis):

1. **Hardware Modality** — Core QPU pure-plays, pre-revenue risk (RGTI, IONQ, QBTS).
2. **Control Systems & RF** — Microwave pulse networks, precision laser delivery, AWG control electronics (KEYS, COHR).
3. **Cryogenics & Environment** — Sub-Kelvin thermal management, dilution refrigeration, rare gas logistics (FORM, LIN).
4. **Upstream Advanced Materials** — ALD tooling, specialized superconductor substrates, ultra-pure chemical deposition (CCJ, ASMI).

Linde appears once, as LIN. The old registry listed it twice (bogus ticker LNDB + LIN); LNDB is not a real ticker. ASMI delisted from Nasdaq — it is fetched as Euronext ASM.AS (EUR-denominated); scorer ratios are currency-invariant, so EUR financials score fine, but allocator prices for ASMI are in EUR (see `docs/DECISIONS.md`).

## 🧮 Quantum Quality Score Engine

`scoring/quantum_scorer.py` calculates a score from 0–100. Bucket coverage is shown everywhere a score is printed (BKTS column), so a 4-of-6 100 is never mistaken for a 6-of-6 100:

* **R&D Intensity** — R&D expense relative to revenue; for pre-revenue names, R&D relative to annual burn.
* **Cash Runway** — Total cash scaled against annual operational burn rate. Cash-flow-positive names score max. Runway under 12 months flags "RUNWAY < 12M", caps the signal at WEAK, and excludes the ticker from the allocator.
* **Revenue Growth** — Year-over-year top-line growth, computed from annual financials. For pre-revenue names this factor is MISSING, never zero and never a made-up default.
* **Gross Margin (level)** — Gross profit / revenue, a snapshot, not a trend. The old README called this "margin direction"; it is not a direction. Missing for pre-revenue names.
* **Dilution** — Share-count growth; heavy dilution lowers the score.
* **Thesis / Milestones** — Manual 0–100 input (qubit counts, error rates, roadmap delivery). Default is missing, never invented.

Weights differ by group (Kevin's call — see `docs/DECISIONS.md`): pure-play R&D 0.30 / runway 0.30 / growth 0.10 / margin 0.05 / dilution 0.10 / thesis 0.15; enabler R&D 0.15 / runway 0.20 / growth 0.20 / margin 0.20 / dilution 0.10 / thesis 0.15. Missing factors are excluded from the average with remaining weights renormalized — missing data is never scored zero.

Signal thresholds: STRONG ≥75 | NEUTRAL 50–74 | WEAK 25–49 | CRITICAL <25.

## ⚙️ Technical Filter Overlay

Before suggesting any capital deployment, allocations run through an execution momentum filter (`data/fetch_fundamentals.py`, RSI-14 with Wilder's smoothing):

* **Trend Gate**: Price must be above its 50-day Simple Moving Average (SMA) for a buy.
* **Momentum Gate**: RSI ≥ 70 flags overbought; RSI ≤ 35 with price above the SMA marks the dip-buying zone.

## 📊 Data

Everything comes through yfinance. There is no SEC EDGAR pipeline and no FMP key — the old ingestion module built a malformed SEC URL and always fell back to hardcoded profiles, so it was deleted. A fetch failure returns None and prints an error; no number is ever invented, substituted, or carried over from a fallback profile. Cached fundamentals live in `data_storage/` (git-ignored).

## 🚀 How to Run

All commands run from the repo root.

* `python -m scoring.quantum_scorer` — Score the full 9-ticker universe and print the table.
* `python -m data.fetch_fundamentals` — Fetch latest fundamentals for the universe into `data_storage/`.
* `python allocator.py` — Order sheet: target weights, share counts, and technical buy signals. Score gate ≥ 50, $10,000 budget.
* `python live_signal.py` — Live trading signal with the same engine. Score gate ≥ 40, $800 budget, SGOV as the defensive holding.
* `python backtester.py` — 14/60/200-day momentum backtest. Compares against a true buy-and-hold benchmark (equal dollars, fixed shares, weights drift). The ungated variants are the honest numbers; the score-gated variants are labeled in-sample, because today's scores judge historical trades.
* `python milestone_tracker.py` — Earnings-date alerts plus hand-entered milestones from `data/milestones.json`.
* `python report.py` — Daily briefing: ranked scores, live signals, runway flags, earnings/milestones, ledger summary.
* `python metrics.py` — Portfolio metrics on the paper-trade ledger.
* `python logger.py` — Paper-trade ledger test (writes to a temp file, never the real ledger).

## 🚀 Repository Blueprint

* `config/universe.py` — The 9-ticker universe, 4 layers, watchlist, Yahoo symbol overrides.
* `config/settings.py` — Data folder and rate-limit constants.
* `scoring/quantum_scorer.py` — The 0–100 composite engine: six factors, per-layer weights, bucket coverage, pre-revenue and runway rules.
* `data/fetch_fundamentals.py` — Fundamentals, RSI-14, 50-day SMA, momentum/drawdown (yfinance).
* `data/trade_log.csv` — Paper-trade ledger, header-only (no real paper trades recorded).
* `data/milestones.json` — Hand-entered thesis milestones (empty template; nothing is ever generated).
* `data/signal_history.json`, `data/drift_history.json` — Signal/drift history (start empty).
* `allocator.py` — Order sheet with target weights, share counts, and technical buy signals.
* `live_signal.py` — Live signal and order sheet for real-time trading decisions.
* `backtester.py` — Momentum backtester with true buy-and-hold benchmark and honest ungated variants.
* `milestone_tracker.py` — Earnings-date alerts and milestone tracking.
* `report.py` — Daily briefing.
* `metrics.py` — Portfolio metrics on the paper-trade ledger.
* `logger.py` — Paper-trade transaction ledger.
* `docs/DECISIONS.md` — Every judgment call from the overhaul, recorded as Kevin's open calls.
* `docs/CHANGELOG.md` — Development tracking ledger. (Note: the file lives in `docs/`, not the repo root.)
* `INVESTMENT_THESIS.md` — Strategy thesis (not rewritten in the overhaul; see DECISIONS.md for contradictions).
* `OPERATIONS_PLAYBOOK.md` — Operations playbook (not rewritten in the overhaul; describes deleted modules).

## Corporate Licensing

This project is licensed under the terms of the MIT License. Ownership and legal copyrights are held strictly by **Second Layer Capital**.
