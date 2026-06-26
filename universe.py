"""
Second Layer Capital - Quantum Screener Universe Registry
File: universe.py (Root Directory)
"""

# Initial strict "picks and shovels" asset universe
QUANTUM_UNIVERSE = {
    "RGTI": {"name": "Rigetti Computing", "layer": "HARDWARE_MODALITY"},
    "IONQ": {"name": "IonQ Inc.", "layer": "HARDWARE_MODALITY"},
    "QBTS": {"name": "D-Wave Quantum", "layer": "HARDWARE_MODALITY"},
    "KEYS": {"name": "Keysight Technologies", "layer": "CONTROL_SYSTEMS_RF"},
    "FORM": {"name": "FormFactor", "layer": "CRYOGENICS_ENVIRONMENT"}
}

if __name__ == "__main__":
    print(f"[✓] Universe file loaded successfully.")
    print(f"Tracking {len(QUANTUM_UNIVERSE)} quantum infrastructure assets.")
