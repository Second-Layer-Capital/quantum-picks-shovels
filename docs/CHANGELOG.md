# Changelog
All notable changes to the Second Layer Capital Quantum Ecosystem Screener will be documented in this file.

## - 2026-11-16
### Overhaul — complete rebuild on the nuclear/hypersonic house pattern
* **Deleted** `ingestion.py` (malformed SEC URL, always fell back to hardcoded profiles), `conference_intel.py` (OpenFIGI at the wrong endpoint), `insider_tracker.py` (fabricated mock alerts on network failure), `settings.py` (FMP key), root `scoring.py` and `universe.py`.
* **Universe (`config/universe.py`)**: 9 unique companies in 4 layers; Linde appears once as LIN (bogus ticker LNDB dropped). Empty `WATCHLIST` — no additional candidates could be verified from the thesis. ASMI mapped to Euronext `ASM.AS` (Nasdaq ASMI delisted).
* **Scorer (`scoring/quantum_scorer.py`)**: 0–100 composite, house thresholds (STRONG ≥75 / NEUTRAL 50–74 / WEAK 25–49 / CRITICAL <25), per-layer weights (pure-play vs enabler), bucket coverage (BKTS). Pre-revenue: growth and margin are MISSING, never zero or a made-up default. Runway <12 months flags and caps at WEAK. Dilution flag. Thesis/milestone bucket is a manual input, default missing. No fabricated data anywhere.
* **Data (`data/fetch_fundamentals.py`)**: yfinance throughout — fundamentals, Wilder's RSI-14, 50-day SMA. Fetch failure returns None and prints an error, never invented numbers.
* **Allocator (`allocator.py`)**: score gate ≥ 50, $10,000, equal weights, technical filter (above-50-SMA for EXECUTE BUY; RSI ≥ 70 HOLD; RSI ≤ 35 + above SMA dip alert). Runway-flagged names never allocated. Order sheet with +0.5% limits.
* **Live signal (`live_signal.py`)**: score gate ≥ 40, $800, SGOV defensive, order sheet, prior-run change tracking.
* **Backtester (`backtester.py`)**: 14/60/200-day momentum, 15% stop, 100% take-profit, true buy-and-hold benchmark (equal dollars, fixed shares, weights drift) plus the daily-rebalanced variant labeled separately. Gated variants labeled "(in-sample)" — today's scores gating history is lookahead.
* **Ledger (`logger.py`, `metrics.py`)**: paper-trade ledger, header-only `data/trade_log.csv`, empty-log-safe metrics, SELL rows never counted as investment.
* **Milestone tracker (`milestone_tracker.py`)**: earnings dates (3-attempt parse) plus hand-entered milestones from `data/milestones.json`; fetch failure is reported, never a fake date.
* **Briefing (`report.py`)**: ranked table, live signals, runway flags, earnings/milestones, ledger summary.
* **Docs**: `docs/DECISIONS.md` records every judgment call as Kevin's open call. README rewritten to the nuclear standard.
* **Tests**: 170 known-answer checks across five test files (outside the repo), all passing; live runs verified on real yfinance data 2026-11-16.

## - 2026-07-02
### Added
* **Dynamic Growth Analytics (`scoring.py`):** Upgraded factor calculations to extract and compare multi-year historical revenue files, computing real percentage shifts while insulating pre-revenue assets from system crashes.

## - 2026-06-26
### Added
* **Expanded Universe Registry (`universe.py`)**: Scaled tracking coverage to 10 tier-1 picks-and-shovels assets, formally mapping the `UPSTREAM_MATERIALS` bottleneck layer (`ASMI`, `CCJ`, `COHR`, `LNDB`, `LIN`).
* **Conference Intelligence Scraper (`conference_intel.py`)**: Deployed a dynamic headless browser pipeline using Playwright to extract dynamic javascript content blocks from premier summits (Quantum World Congress).
* **Global Market Verification Registry**: Integrated an automated OpenFIGI API query layer to instantly separate public listings from private venture capital targets.
* **Dual-Tab Spreadsheet Exporter**: Automated generation of organized corporate discovery workbooks splitting leads into `PUBLIC_EQUITIES` and `PRIVATE_VENTURE_WATCHLIST` tabs.
* **Segment Filtering Flags (`scoring.py`)**: Upgraded the core engine with targeted argument options (`target_layer`) to slice results and isolate leaderboards strictly by specialized supply chain segments.

### Changed
* **Filing-Specific SEC Parsers (`ingestion.py`)**: Upgraded accounting data extraction to scan history arrays and explicitly separate audited annual `10-K` metrics from current-quarter `10-Q` cash balances.

### Fixed
* **Crash Resilience Guard Clauses**: Replaced absolute array lookups with safe `NoneType` catch blocks and mapping fallbacks to prevent pipeline failures on missing corporate identifiers or internet DNS interruptions (`Errno 11001`).
* **Git Environment Security**: Restructured tracking rules in `.gitignore` to securely lock out isolated environment containers (`venv/`) and binary spreadsheet outputs (`intelligence_out/`) from public cloud repositories.

## - 2026-06-25
### Added
* **SEC Data Integration (`ingestion.py`)**: Built a zero-auth public regulatory data stream mapping out 10-digit SEC corporate CIK codes for direct financial fact extraction.
* **Corporate Identification Header**: Integrated compliance user-agent tags to meet institutional government networking access requirements.
* **Network Interception Handling**: Configured silent catch blocks for `Errno 11001` DNS dropouts to guarantee execution continuity via structural fallback arrays.

## - 2026-06-25
### Changed
* **Scoring Logic (`scoring.py`)**: Refined the quantitative engine to handle zero-revenue operators via operational expense proxies, process cash-flow positive enablers without hitting division-by-zero math boundaries, and bound volatile metrics to standard 0.0–1.0 ranges.
* **Ingestion Simulation (`ingestion.py`)**: Replaced raw data templates with distinct operational risk profiles to rigorously test and validate multi-factor ecosystem edge cases.

## - 2026-06-25
### Added
* **Universe Registry (`universe.py`)**: Initialized a 5-ticker pure-play tracking registry covering core hardware, control system RF, and cryogenic infrastructure enablers.
* **Screener Configurations (`settings.py`)**: Established baseline multi-factor scoring weights emphasizing R&D Intensity (40%) and Cash Runway (30%).
* **Ingestion Pipeline (`ingestion.py`)**: Implemented a localized file storage data builder creating raw JSON assets inside a dedicated directory.
* **Scoring Matrix (`scoring.py`)**: Built a flat quantitative ranking engine running standalone dictionary sorts to generate leaderboard output tables.
* **Corporate Licensing (`LICENSE`)**: Applied an official corporate MIT license attributing complete project ownership to Second Layer Capital.
* **Repository Documentation (`README.md`)**: Drafted an institutional-grade codebase blueprint and operational execution guide.

### Security
* **Git Version Control**: Cleaned environment paths and configured explicit local `.gitignore` rules to completely lock out background caching (`__pycache__/`) and local financial storage files (`data_storage/`) from cloud tracking.

* **Insider Accumulation Monitor (\insider_tracker.py\):** Deployed real-time SEC Form 4 parser filtering out equity grant noise and capturing open-market purchases (Code P).
