"""
Second Layer Capital - Quantum Quantitative Scoring Engine
File: scoring.py (Root Directory)
"""

import os
import json
from universe import QUANTUM_UNIVERSE
from settings import DATA_FOLDER, SCORING_WEIGHTS

def calculate_scores():
    print("Initializing Quantum Screener Scoring Matrix...\n")
    final_rankings = []

    for ticker, meta in QUANTUM_UNIVERSE.items():
        file_path = os.path.join(DATA_FOLDER, f"{ticker}_data.json")
        
        # Guard clause in case a dataset file is missing
        if not os.path.exists(file_path):
            print(f" [!] Skipping {ticker}: Dataset file not found.")
            continue
            
        with open(file_path, "r") as f:
            data = json.load(f)
            
        # 1. R&D Intensity (R&D / Revenue)
        rd_intensity = data["research_and_development"] / data["revenue"] if data["revenue"] > 0 else 0
        
        # 2. Cash Runway (Total Cash / Annual Burn)
        cash_runway = data["total_cash"] / data["annual_burn_rate"] if data["annual_burn_rate"] > 0 else 0
        
        # 3. Gross Margin (Gross Profit / Revenue) - proxy for Margin Direction
        gross_margin = data["gross_profit"] / data["revenue"] if data["revenue"] > 0 else 0
        
        # Mock Revenue Growth baseline for structural testing
        rev_growth = 0.20 

        # Component Weighted Score Calculation
        total_score = (
            (rd_intensity * SCORING_WEIGHTS["RD_INTENSITY"]) +
            (cash_runway * SCORING_WEIGHTS["CASH_RUNWAY"]) +
            (rev_growth * SCORING_WEIGHTS["REVENUE_GROWTH"]) +
            (gross_margin * SCORING_WEIGHTS["MARGIN_DIRECTION"])
        )

        final_rankings.append({
            "ticker": ticker,
            "name": meta["name"],
            "layer": meta["layer"],
            "final_score": round(total_score, 4),
            "rd_intensity": round(rd_intensity, 2),
            "runway_years": round(cash_runway, 1)
        })

    # Sort rankings strictly by final score in descending order
    final_rankings.sort(key=lambda x: x["final_score"], reverse=True)

    # Display final results table
    print(f"{'RANK':<5}{'TICKER':<8}{'ECOSYSTEM LAYER':<25}{'SCORE':<10}{'R&D INT':<10}{'CASH RUNWAY':<12}")
    print("-" * 70)
    for index, item in enumerate(final_rankings, 1):
        print(f"{index:<5}{item['ticker']:<8}{item['layer']:<25}{item['final_score']:<10}{item['rd_intensity']:<10}{str(item['runway_years'])+' Yrs':<12}")

if __name__ == "__main__":
    calculate_scores()
