"""
Quantum Picks & Shovels — Ticker Universe
Second book under Second Layer Capital.
Mirrors the layer structure in INVESTMENT_THESIS.md — keep both in sync.

Layers (thesis Section 1):
  HARDWARE_MODALITY       -- Layer 1, core QPU pure-plays (pre-revenue risk)
  CONTROL_SYSTEMS_RF      -- Layer 2, control systems & RF electronics (enablers)
  CRYOGENICS_ENVIRONMENT  -- Layer 3, cryogenics & thermal environment (enablers)
  UPSTREAM_MATERIALS      -- Layer 4, upstream advanced materials (enablers)

CORRECTION vs the old root-level universe.py: Linde plc appears ONCE, as LIN
(the old file listed it twice — bogus ticker LNDB in CRYOGENICS_ENVIRONMENT
and LIN again in UPSTREAM_MATERIALS — and the thesis itself writes
"Linde plc (LNDB/LIN)". LNDB is not a real ticker; Linde trades as LIN.
LIN is kept in CRYOGENICS_ENVIRONMENT, where the thesis places its
helium-3 / cryogenic-gas logistics role.
"""

QUANTUM_UNIVERSE = {
    # --- HARDWARE MODALITY (Layer 1: core QPU pure-plays) ---
    "RGTI": {"name": "Rigetti Computing", "layer": "HARDWARE_MODALITY"},
    "IONQ": {"name": "IonQ", "layer": "HARDWARE_MODALITY"},
    "QBTS": {"name": "D-Wave Quantum", "layer": "HARDWARE_MODALITY"},

    # --- CONTROL SYSTEMS & RF ELECTRONICS (Layer 2: enablers) ---
    "KEYS": {"name": "Keysight Technologies", "layer": "CONTROL_SYSTEMS_RF"},
    "COHR": {"name": "Coherent Corp.", "layer": "CONTROL_SYSTEMS_RF"},

    # --- CRYOGENICS & ENVIRONMENT (Layer 3: enablers) ---
    "FORM": {"name": "FormFactor", "layer": "CRYOGENICS_ENVIRONMENT"},
    "LIN": {"name": "Linde plc", "layer": "CRYOGENICS_ENVIRONMENT"},

    # --- UPSTREAM MATERIALS (Layer 4: enablers) ---
    "CCJ": {"name": "Cameco Corp.", "layer": "UPSTREAM_MATERIALS"},
    "ASMI": {"name": "ASM International", "layer": "UPSTREAM_MATERIALS"},
}

# Yahoo Finance symbol overrides. ASMI delisted from Nasdaq — its only
# liquid listing is now Euronext Amsterdam as ASM (ASM.AS, EUR-denominated).
# yfinance returns "No data found, symbol may be delisted" for plain ASMI.
# Ratios in the scorer are currency-invariant, so EUR financials score
# fine; prices from ASM.AS are in EUR — the allocator treats them as-is
# and the currency mismatch is a known limitation (see DECISIONS.md).
YFINANCE_SYMBOLS = {
    "ASMI": "ASM.AS",
}

# Layer grouping, mirroring the nuclear universe.py domain-keyed structure.
LAYERS = {
    "HARDWARE_MODALITY": {
        "layer_name": "Hardware Modality (Core QPU Pure-Plays)",
        "tickers": ["RGTI", "IONQ", "QBTS"],
        "pre_revenue": True,
    },
    "CONTROL_SYSTEMS_RF": {
        "layer_name": "Control Systems & RF Electronics",
        "tickers": ["KEYS", "COHR"],
        "pre_revenue": False,
    },
    "CRYOGENICS_ENVIRONMENT": {
        "layer_name": "Cryogenics & Thermal Environment",
        "tickers": ["FORM", "LIN"],
        "pre_revenue": False,
    },
    "UPSTREAM_MATERIALS": {
        "layer_name": "Upstream Advanced Materials & Isotopes",
        "tickers": ["CCJ", "ASMI"],
        "pre_revenue": False,
    },
}

# No additional watchlist candidates could be verified from the thesis —
# do NOT add any ticker you cannot verify exists.
WATCHLIST = {}

ALL_TICKERS = [t for layer in LAYERS.values() for t in layer["tickers"]]

# Enablers are the profitable large-caps (layers 2-4); pure-plays are the
# pre-revenue hardware names (layer 1). The scorer weights factors
# differently for the two groups — see scoring/quantum_scorer.py.
ENABLER_LAYERS = {"CONTROL_SYSTEMS_RF", "CRYOGENICS_ENVIRONMENT", "UPSTREAM_MATERIALS"}
PURE_PLAY_LAYERS = {"HARDWARE_MODALITY"}

PURE_PLAY_TICKERS = [t for t in ALL_TICKERS
                     if QUANTUM_UNIVERSE[t]["layer"] in PURE_PLAY_LAYERS]
ENABLER_TICKERS = [t for t in ALL_TICKERS
                   if QUANTUM_UNIVERSE[t]["layer"] in ENABLER_LAYERS]


def get_layer_for_ticker(ticker):
    """Returns the layer key a ticker belongs to, or None if not in universe."""
    entry = QUANTUM_UNIVERSE.get(ticker)
    return entry["layer"] if entry else None
