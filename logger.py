"""
Quantum Picks & Shovels Screener — Paper-Trade Ledger
Second Layer Capital

Appends paper trades to data/trade_log.csv.

Columns: date, ticker, action, shares, price, total
  date   — YYYY-MM-DD HH:MM at time of logging (or the date passed in)
  ticker — uppercased symbol
  action — BUY or SELL (uppercased; anything else is rejected)
  shares — number of shares (rounded to 4 dp)
  price  — execution price per share
  total  — shares * price, rounded to 2 dp

record_trade() takes an optional log_file param (default
data/trade_log.csv) so tests never touch the real ledger.
"""

import csv
import os
from datetime import datetime

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
LOG_FILE = os.path.join(BASE_DIR, "data", "trade_log.csv")

HEADER = ["date", "ticker", "action", "shares", "price", "total"]


def initialize_log(log_file=None):
    """Create the CSV file with column headers if it doesn't exist yet."""
    path = log_file or LOG_FILE
    if not os.path.exists(path):
        parent = os.path.dirname(path)
        if parent:
            os.makedirs(parent, exist_ok=True)
        with open(path, mode="w", newline="") as f:
            writer = csv.writer(f)
            writer.writerow(HEADER)


def record_trade(ticker, action, shares, price, log_file=None, date=None):
    """Log a single paper trade into the ledger.

    log_file overrides the ledger path — used by tests so a test
    trade never lands in the real ledger. Omit it for real trades.
    date overrides the timestamp (YYYY-MM-DD HH:MM string, or a
    datetime); defaults to now. Returns the row written, as a dict.
    """
    action = str(action).upper()
    if action not in ("BUY", "SELL"):
        raise ValueError(f"action must be BUY or SELL, got {action!r}")
    shares = round(float(shares), 4)
    price = float(price)
    if shares <= 0:
        raise ValueError(f"shares must be positive, got {shares}")
    if price <= 0:
        raise ValueError(f"price must be positive, got {price}")
    total = round(shares * price, 2)

    if date is None:
        date_str = datetime.now().strftime("%Y-%m-%d %H:%M")
    elif isinstance(date, datetime):
        date_str = date.strftime("%Y-%m-%d %H:%M")
    else:
        date_str = str(date)

    path = log_file or LOG_FILE
    initialize_log(log_file=path)

    row = {
        "date": date_str,
        "ticker": str(ticker).upper(),
        "action": action,
        "shares": shares,
        "price": price,
        "total": total,
    }
    with open(path, mode="a", newline="") as f:
        writer = csv.writer(f)
        writer.writerow([row["date"], row["ticker"], row["action"],
                         row["shares"], row["price"], row["total"]])

    print(f"LOGGED: {action} {shares} shares of {row['ticker']} "
          f"at ${price} (total ${total})")
    return row


if __name__ == "__main__":
    # Demo only. The test trade goes to a throwaway file, NOT the
    # real ledger — the old repo's ledger held exactly one fake test
    # row, and this ledger starts empty on purpose.
    import tempfile
    print("Testing paper log framework (test trade goes to a temp file, "
          "not data/trade_log.csv)...")
    with tempfile.TemporaryDirectory() as tmp:
        test_log = os.path.join(tmp, "trade_log_test.csv")
        record_trade(ticker="RGTI", action="BUY", shares=10,
                     price=15.50, log_file=test_log)
        with open(test_log) as f:
            print(f.read().strip())
    print("Test complete — data/trade_log.csv untouched.")
