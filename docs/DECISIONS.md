# DECISIONS — Quantum Picks & Shovels Overhaul (2026-11-16)

Every judgment call made during the 2026-11-16 overhaul, recorded so Kevin
can approve, change, or reject each one. Nothing here is settled until he
says so. Values copied from the nuclear/hypersonic repos are marked as
such — copying is not approval.

## 2026-11-16 — Complete overhaul (branch muse/quantum-overhaul)

The old code was not salvageable as a pipeline: `ingestion.py` built a
malformed SEC URL (`https://sec.gov{cik}.json`) and always fell back to
hardcoded profiles; revenue growth was hardcoded 0.15 on the live path;
"margin direction" was a static margin level; the universe listed Linde
twice (bogus ticker LNDB + LIN); OpenFIGI was queried at the wrong
endpoint; `insider_tracker.py` fabricated mock alerts on network
failure. Deleted: `ingestion.py`, `conference_intel.py`,
`insider_tracker.py`, `settings.py`, root `scoring.py`, root
`universe.py`. Rebuilt on the nuclear/hypersonic house pattern
(yfinance throughout, 0–100 composite scores, allocator + live signal +
backtester + paper ledger + daily briefing, known-answer tests).

### Scoring weights (scoring/quantum_scorer.py) — KEVIN'S CALL

- Pure-play (HARDWARE_MODALITY): R&D 0.30, runway 0.30, growth 0.10,
  margin 0.05, dilution 0.10, thesis 0.15.
- Enabler (all other layers): R&D 0.15, runway 0.20, growth 0.20,
  margin 0.20, dilution 0.10, thesis 0.15.
- Both sum to 1.0. Rationale: survival + R&D dominate for pre-revenue
  names; growth and margin level are real, comparable numbers for
  profitable enablers. Live consequence, verified 2026-11-16: the
  pure-plays score 84–100 and the enablers 63–81, so the ranking puts
  pre-revenue names above profitable ones by design.

### Pre-revenue rule — SETTLED (thesis §3.1)

Zero/None revenue → revenue growth and gross margin score MISSING
(None), excluded from the average with remaining weights renormalized.
Never zero, never a made-up default (the old code defaulted growth to
0.20; that bug is the reason this rule exists). R&D intensity for a
pre-revenue name is scored as R&D / annual burn (share of burn that is
R&D) on the same ladder as R&D / revenue — open call: Kevin may prefer
the factor missing instead (one-line change). Negative revenue is
treated as zero revenue (pre-revenue path), not as missing data.

### Cash runway gate — KEVIN'S CALL

Runway under 12 months adds flag "RUNWAY < 12M", caps the signal at
WEAK, and the allocator excludes the ticker entirely. Burn is
|annual operating cash flow| when negative, else 0 (nuclear's
pre-revenue convention). Note the thesis (§3.2) warns at 1.5–2.0 years,
not 12 months — the 12-month hard flag is stricter than the thesis
warning band; whether the flag should move to 18 months is open.
Open: burn ≤ 0 scores 100 on runway, which treats a loss-making
enabler the same as a profitable one when burn is derived from
operating cash flow. Nuclear scores a negative-EBITDA name 0 on its
runway bucket (known-bad, not missing) — should quantum do the same?

### Thesis / milestone bucket — KEVIN'S CALL

Manual 0–100 `thesis_score` input, default None (missing, never
invented). No source exists yet. Open: where does it come from — a
manual overrides file, conference intel, insider signal? Who
maintains it? `data/milestones.json` holds hand-entered milestones
only (qubit counts, error rates, roadmap items); the file ships empty
with an example block.

### Gross margin is a LEVEL — SETTLED (honesty fix)

The old README called it "margin direction" / "trend lines". The code
computes gross_profit / revenue, a snapshot. It is labeled "gross
margin (level)" everywhere now. No historical margin comparison exists.

### Gates and capital — KEVIN'S CALL (copied from nuclear)

- Allocator: score gate ≥ 50, $10,000 capital (nuclear's values).
- Live signal: score gate ≥ 40, $800 capital (nuclear's values).
- Backtester: score gate 40 (nuclear backtester's value).
- House standard across modules is still open (same question as the
  nuclear audit). Quantum names are earlier-stage than nuclear's, so a
  lower allocator gate may fit.
- Defensive asset: SGOV (the asset nuclear's backtester validated).
  Nuclear's live signal uses USFR — the alternative.
- Live signal: a None score does NOT fail the gate (nuclear's
  convention — unscored names can qualify on momentum alone, ranked
  last). The allocator is stricter and requires score ≥ gate.
- WAIT/HOLD names get 0 shares and their budget stays cash (differs
  from nuclear's allocator, which allocates anyway). In a weak market
  most capital sits idle — verified live 2026-11-16: only LIN bought,
  $1,057 of $10,000 deployed.

### Backtester — KEVIN'S CALL

- Momentum windows 14/60/200 days, 15% trailing stop, 100% take-profit,
  0.05% slippage, equal-weight baskets, SGOV defensive (all nuclear's
  values).
- True buy-and-hold benchmark: equal dollars in, shares fixed, weights
  drift. The daily-rebalanced equal-weight variant is kept as a
  separate labeled function so the construction gap stays visible
  (verified live: 60D window, rebalanced 411.6% vs true B&H 98.5% —
  the gap is benchmark construction, not strategy).
- Gated variants are labeled "(in-sample)" in every output line: the
  gate is today's scores applied to history (lookahead). Currently the
  gate filters nothing (lowest live score 63.7 ≥ 40) — keep or drop the
  gated variant is the same open question as nuclear.
- No IPO floors: no verified floor dates exist (RGTI/QBTS came via
  SPACs); SPAC-shell history is accepted rather than invented.
- No equity-curve chart (nuclear writes a PNG). Add on Kevin's word.
- Gate failure exits 0, not 2 (nuclear exits 2) — the gated variant is
  diagnostic-only here.
- Survivorship stands: today's 9 tickers run back to 2022; delisted
  quantum names never appear. No fix available in-repo.

### ASMI ticker — KEVIN'S CALL

ASMI delisted from Nasdaq — yfinance returns "No data found, symbol
may be delisted" for plain ASMI. Mapped in `config/universe.py`
(`YFINANCE_SYMBOLS = {"ASMI": "ASM.AS"}`): the live listing is
Euronext Amsterdam, EUR-denominated. Scorer ratios are
currency-invariant, so EUR financials score fine. Prices from ASM.AS
are in EUR and the allocator/live signal/backtester treat them as-is
(a known limitation, flagged here, not hidden). Alternatives: drop
ASMI (8 names), or use OTC ASMXF (thin). Verified live 2026-11-16:
ASMI fetches, scores 73.0, backtests with 9 tickers, earnings date
2027-02-23.

### Coverage vs score — KEVIN'S CALL

Live 2026-11-16: QBTS scores 100.0 on 4/6 buckets (thesis and dilution
missing). The caps saturate — a pre-revenue name maxes every available
factor. The BKTS column shows the coverage, but the score itself does
not. Should a score be capped by coverage (same class as nuclear's
single-bucket-100 question)?

### Ledger and history files

- `data/trade_log.csv` ships header-only and is committed (differs
  from nuclear, which gitignores it — the task required the file as a
  deliverable; it is empty).
- `signal_state.json` is gitignored (runtime artifact, like nuclear).
- `data/signal_history.json` and `data/drift_history.json` start as
  `{}` (hypersonic's ticker → list shape).

### Thesis / playbook contradictions (flagged, not fixed)

`INVESTMENT_THESIS.md` and `OPERATIONS_PLAYBOOK.md` were left in place
and NOT rewritten. They now contradict the new code:

- Thesis writes "Linde plc (LNDB/LIN)" — LNDB is not a real ticker.
- Thesis §3.2 warns on runway below 1.5–2.0 years; the code flags
  below 12 months.
- Thesis §3.4 calls open-market insider purchases (Code P) "the single
  most reliable forward indicator" — the insider module was deleted
  (it fabricated data) and not rebuilt.
- The playbook describes deleted modules (`ingestion.py`,
  `conference_intel.py`, `insider_tracker.py`, `settings.py` / FMP
  key) and the old execution sequence. It does not describe any new
  module.
- These documents need a rewrite on Kevin's word; the README points
  at the thesis as the strategy source in the meantime.
