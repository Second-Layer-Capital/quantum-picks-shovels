PROPERTY OF SECOND LAYER CAPITAL | CONSTITUTES PROPRIETARY SPECIFICATIONS | DO NOT DISTRIBUTE OUTSIDE AUTHORIZED CHANNELS


# MASTER PLAYBOOK I: SYSTEMS OPERATIONS & COMPLIANCE ARCHITECTURE
### DOCUMENT REF: SLC-OPS-UG-2026-V1.2 | SYSTEM: QUANTUM SUPPLY CHAIN SCREENER ENGINE
### SECURITY CLASSIFICATION: PROPRIETARY & CONFIDENTIAL | VERSION: 1.2.0

---

## SECTION 1: CODEBASE TOPOLOGY & FILE RECOGNITION

The system operates strictly within a flat-file architecture to eliminate Windows environment pathing and relative module cross-import failures. All executable scripts communicate directly within the project's root folder environment.

```text
quantum-picks-shovels/
├── .gitignore               # Plaintext system rules isolating operational data & cache from cloud
├── CHANGELOG.md             # Development tracking ledger auditing version history additions
├── LICENSE                  # Legal corporate MIT documentation allocating ownership to Second Layer Capital
├── README.md                # System architectural summary and structural project blueprint
├── PROFILE_README.md        # Formatted template tracking institutional executive layout configuration
├── universe.py              # Central core asset tracking registry mapping 10 structural play tickers
├── settings.py              # Quant allocation rules, factor weights, and target endpoint connections
├── ingestion.py             # Form-specific SEC Edgar data processing & socket fallback engine
├── scoring.py               # Analytical leaderboard processor executing metric normalization filters
├── conference_intel.py      # Playwright dynamic web scraper integrated with OpenFIGI validation arrays
├── insider_tracker.py       # Real-time SEC Form 4 Stream Analyzer isolating Transaction Code "P" alerts
└── venv/                    # Local runtime container isolating system library dependencies (Git Ignored)
```

---

## SECTION 2: PRODUCTION ENVIRONMENT INITIALIZATION

To protect your system from global library corruption, the application must run exclusively inside an isolated environment wrapper.

### Step 2.1: Terminal Initialization & Execution Policy Override
Open an elevated Windows PowerShell terminal and execute the Process-level execution policy bypass to permit local script initialization:
```powershell
Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope Process -Force
cd C:\Users\kevin\quantum-picks-shovels\
```

### Step 2.2: Environment Container Deployment
Instantiate a clean, local virtual python environment and permanently update the tracking block configuration:
```powershell
python -m venv venv
.\venv\Scripts\Activate.ps1
```
*Verification Check:* Your active prompt line must display the `(venv)` tag prefix on the left side of your path.

### Step 2.3: Production Package Serialization
Deploy and freeze the core package binaries inside your environment:
```powershell
pip install playwright pandas openpyxl
playwright install chromium
```

---

## SECTION 3: SYSTEM OPERATIONAL STEP-BY-STEP SEQUENCE

### Step 3.1: Upstream Asset Extraction (Web Intelligence Monitoring)
Execute the dynamic conference intelligence pipeline to crawl global summit matrices (e.g., Quantum World Congress) and separate listed public companies from private targets:
```powershell
python .\conference_intel.py
```
* **System Action Under the Hood:** Playwright instantiates a headless Chromium browser layer, bypasses dynamic JavaScript view wrappers, and captures text fields. The records ping the OpenFIGI REST endpoint via native payload structures, filtering out core conglomerates (e.g., Google, IBM) to isolate pure-play assets.
* **Output Path:** The file writes directly as a dual-tab spreadsheet to:
  `C:\Users\kevin\quantum-picks-shovels\intelligence_out\quantum_world_congress_discovery.xlsx`

### Step 3.2: SEC Audit Data Synchronization (Ingestion Phase)
Run the automated SEC Edgar public extraction array to pull the audited financial statements for our 10-stock universe:
```powershell
python .\ingestion.py
```
* **System Action Under the Hood:** The engine handles automated header injection (`User-Agent: Second Layer Capital...`) to remain in full compliance with public extraction limits. It runs an explicit search algorithm isolating audited annual `10-K` forms for top-line revenue, R&D expenses, and net profit configurations, while checking latest `10-Q` filings for current liquid cash balances.
* **Output Path:** Captured variables are written out as clean local JSON profiles to the `data_storage/` folder.

### Step 3.3: Quantitative Synthesis Execution (Scoring Engine)
Execute the mathematical screening engine to generate your multi-factor ecosystem leaderboards:
```powershell
python .\scoring.py
```
* **System Action Under the Hood:** The engine parses each company's JSON data, calculates four distinct corporate safety metrics, bounds the scores safely between `0.0` and `1.0` using custom mathematical caps, applies any sector-specific layer filters, and ranks the entire supply chain layout in descending order.

### Step 3.4: Tactical Insider Purchase Sweeps
Execute the real-time Form 4 tracking array to isolate open-market director transactions:
```powershell
python .\insider_tracker.py
```
* **System Action Under the Hood:** Scans public regulatory notification pipelines, bypasses standard stock compensation noise (Transaction Codes `A`, `M`, and `S`), and targets open-market purchases (Code `P`) made with personal capital.

---

## SECTION 4: EXPLICIT FAILURE INTERCEPTION & ERROR HANDBOOKS

### Case 4.1: Network Access Refusal (`HTTP Error 401: Unauthorized`)
* **Root Cause:** A commercial data vendor has rejected your connection payload because your `settings.py` parameter contains an expired or generic placeholder token (`API_KEY = "demo"`).
* **System Response:** The ingestion pipeline automatically intercepts this failure inside its network loop, issues a soft alert to the terminal console, and immediately switches to your pre-configured structural test scenarios to prevent a runtime crash.
* **Remediation:** To route back to live vendor APIs, obtain an updated commercial token and assign it to the environment space using: `[System.Environment]::SetEnvironmentVariable('FMP_API_KEY', 'YOUR_KEY_HERE', 'Process')`.

### Case 4.2: Local Socket Disconnects (`Errno 11001: getaddrinfo failed`)
* **Root Cause:** Your local Windows network adapter or DNS layer has dropped connectivity to the public SEC or OpenFIGI database endpoints during a terminal scan.
* **System Response:** The application's native exception-catching loop stops the terminal from throwing a hard traceback crash, maintains processing momentum, and pulls the local fallback structural profiles directly from disk memory.
* **Remediation:** Verify your local Windows adapter connection status or flush your DNS table via `ipconfig /flushdns` in an external terminal window before re-executing your data sync.

### Case 4.3: Persistent Repository Routing Loops (`fatal: repository not found`)
* **Root Cause:** The system's local Git hidden environment configuration has cached an incorrect or truncated repository domain address (e.g., `https://github.com`).
* **Remediation Protocol:** Do not attempt automated push adjustments. Run this explicit manual override sequence to reset your cloud endpoints:
  ```powershell
  git remote remove origin
  git remote add origin https://github.com
  git push -u origin main
  ```



END OF FILE SLC-OPS-UG-2026-V1.2 | LICENSED AND UNDER EXCLUSIVE COPYRIGHT BY SECOND LAYER CAPITAL (2026) | ALL RIGHTS RESERVED
