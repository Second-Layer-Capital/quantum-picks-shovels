# Quantum Computing Ecosystem Screener
### Second Layer Capital | Quantitative Research Framework

A robust, flat-file quantitative stock screening framework designed to systematically isolate and evaluate strategic "picks and shovels" supply chain bottlenecks across the quantum computing industrial complex.

## 🏗️ Core Ecosystem Layers
The screener tracks and segments the global quantum infrastructure architecture across four high-alpha dependency vectors:
1. **Hardware Modality**: Core quantum processing units (Trapped Ion, Superconducting, Annealing QPUs).
2. **Control Systems & RF**: Microwave pulse networks, precision laser delivery, and AWG control electronics.
3. **Cryogenics & Environment**: Sub-Kelvin thermal management systems, dilution refrigeration, and rare gas logistics (Helium-3).
4. **Upstream Advanced Materials**: Atomic layer deposition (ALD) tooling, specialized superconductor substrates, and ultra-pure chemical deposition.

## 🧮 Quantitative Evaluation Strategy
Assets are evaluated utilizing a robust, edge-case insulated mathematical matrix that caps volatile metrics between `0.0` and `1.0` to eliminate outlier skews:
* **R&D Intensity (40%)**: Research and Development expenses relative to top-line Revenue (utilizing absolute cash burn fallbacks for zero-revenue pure-plays).
* **Cash Runway (30%)**: Liquid cash and short-term reserves scaled against annual operational net burn rate (with automated max-safety scoring for cash-flow positive enablers).
* **Revenue Growth (15%)**: Realized Year-over-Year top-line traction.
* **Margin Direction (15%)**: Gross profit optimization trend lines.

## 📂 Project Architecture
```text
quantum-picks-shovels/
├── data_storage/        # Local SEC operational JSON cache (Git Ignored)
├── intelligence_out/    # Dual-tab conference discovery Excel workbooks (Git Ignored)
├── venv/                # Isolated virtual environment folder (Git Ignored)
├── universe.py          # 10-stock active supply chain asset registry 
├── settings.py          # Operational factor weights, thresholds, and delays
├── ingestion.py         # Form-specific (10-K/10-Q) SEC Edgar extraction pipeline
├── scoring.py           # Multi-factor matrix ranking with segment filtering flags
├── conference_intel.py  # Playwright headless browser + OpenFIGI cross-referencing scraper
├── CHANGELOG.md         # Corporate development tracking ledger
└── LICENSE              # MIT Corporate License (Second Layer Capital)
```

## ⚙️ Operational Execution
Ensure your isolated virtual environment is active before running the automation layer:
```powershell
# 1. Activate your environment
.\venv\Scripts\Activate.ps1

# 2. Extract company leads from dynamic conference portals via Playwright & OpenFIGI
python .\conference_intel.py

# 3. Pull audited annual 10-K and quarterly 10-Q metrics from SEC database
python .\ingestion.py

# 4. Compute multi-factor matrix and apply segment filters
python .\scoring.py
```

## 📜 Corporate Licensing
This project is licensed under the terms of the MIT License. Ownership and legal copyrights are held strictly by **Second Layer Capital**.
