"""
Second Layer Capital - Quantum Screener Configuration
File: settings.py (Root Directory)
"""

# Hard targets for processing and scoring algorithms
DATA_FOLDER = "data_storage"

# Strategic operational metrics weighting (Must equal 1.0)
SCORING_WEIGHTS = {
    "RD_INTENSITY": 0.40,      # R&D Expense / Total Revenue
    "CASH_RUNWAY": 0.30,       # Total Cash / Annual Net Burn Rate
    "REVENUE_GROWTH": 0.15,    # Year-over-Year Revenue Growth
    "MARGIN_DIRECTION": 0.15   # Gross Margin optimization
}

if __name__ == "__main__":
    print(f"[✓] Settings file loaded successfully.")
    print(f"Total strategic metric allocation: {sum(SCORING_WEIGHTS.values()) * 100}%")

