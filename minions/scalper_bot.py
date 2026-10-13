"""Scalper Bot — dedicated intraday scalper for stocks.

Pulls live quotes from data_feed, runs each ticker through scoring_engine,
and executes only when the score clears 70 with a catalyst inside two weeks.
Position size: 1% of book. Exit: take-profit 0.8%, stop-loss 0.4%.
"""

from data_feed import get_quotes
from scoring_engine import score_ticker
from minions.risk import check_position
from minions.news_wire import best_catalyst_score


TAKE_PROFIT = 0.008   # 0.8%
STOP_LOSS = 0.004     # 0.4%
MIN_SCORE = 70
POSITION_PCT = 0.01   # 1% of book


def scan(tickers, book_value):
    """Return ranked scalp candidates that clear all gates."""
    candidates = []
    for t in tickers:
        q = get_quotes(t)
        if not q:
            continue
        s = score_ticker(t, q)
        cat = best_catalyst_score(t)
        if s >= MIN_SCORE and cat:
            size = round(book_value * POSITION_PCT / q["price"], 2)
            risk = check_position(t, size, q["price"])
            if risk["approved"]:
                candidates.append({
                    "ticker": t,
                    "score": s,
                    "catalyst": cat,
                    "entry": q["price"],
                    "size": size,
                    "take_profit": round(q["price"] * (1 + TAKE_PROFIT), 2),
                    "stop_loss": round(q["price"] * (1 - STOP_LOSS), 2),
                })
    candidates.sort(key=lambda c: c["score"], reverse=True)
    return candidates


def execute(candidate, broker):
    """Place the order through the broker. Stub — wire to Robinhood API."""
    print(f"SCALP {candidate['ticker']} x{candidate['size']} @ {candidate['entry']} "
          f"TP {candidate['take_profit']} SL {candidate['stop_loss']}")
    return {"status": "pending", "candidate": candidate}


if __name__ == "__main__":
    demo_book = 10000
    demo_tickers = ["SPY", "QQQ", "IWM", "AAPL", "MSFT", "NVDA", "AMD", "TSLA"]
    for c in scan(demo_tickers, demo_book):
        execute(c, broker=None)
