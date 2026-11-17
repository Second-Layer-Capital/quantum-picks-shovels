"""
Quantum Picks & Shovels — Configuration
Second book under Second Layer Capital.

Holds the small operational constants the fetch layer needs. The old root
settings.py (FMP API key, SEC endpoint strings) is deleted — this repo
fetches everything through yfinance, which needs no key.
"""

import os
from pathlib import Path

# File System Paths
BASE_DIR = Path(__file__).resolve().parent.parent
DATA_FOLDER = os.path.join(str(BASE_DIR), "data_storage")

# Operational Rate Limiting Safeguards
TIMEOUT_SECONDS = 15
RATE_LIMIT_DELAY = 1.0  # Safe 1-second delay execution between HTTP requests
