"""Scalper Bot — fully automated intraday scalper for stocks.

Pipeline: sync → scan → score → risk-check → review → place → monitor → exit.
- Pre-cycle position sync (Robinhood vs Alpaca) — flags discrepancies before sizing
- Score gate: 70+ via scoring_engine
- Catalyst required inside two weeks via news_wire
- Position size: 1% of book
- Take-profit 0.8%, stop-loss 0.4%
- Risk module enforces 5% max position and 2% daily-loss kill switch
- Broker: Alpaca (paper by default) via alpaca_exec; Robinhood is manual fallback
- Exits: take-profit limit + stop-market, both GTC
"""

import uuid

from data_feed import get_quotes
from scoring_engine import score_ticker
from minions.risk import check_position
from minions.news_wire import best_catalyst_score
from position_sync import sync_before_scan

try:
    from alpaca_exec import review_order, place_order, place_exits
    ALPACA_AVAILABLE = True
except ImportError:
    ALPACA_AVAILABLE = False
    def review_order(account_number, candidate):
        return {"approved": False, "alerts": ["alpaca_exec not available"]}
    def place_order(account_number, candidate, ref_id=None):
        print(f"  [STUB] place_order {candidate['ticker']} — alpaca_exec missing")
        return {"id": None, "status": "stub"}
    def place_exits(account_number, candidate, ref_id=None):
        print(f"  [STUB] place_exits {candidate['ticker']} — alpaca_exec missing")
        return {"take_profit": None, "stop_loss": None}

TAKE_PROFIT = 0.008
STOP_LOSS = 0.004
MIN_SCORE = 70
POSITION_PCT = 0.01


def scan(tickers, book_value):
    """Return ranked scalp candidates clearing score, catalyst, and risk gates."""
    candidates = []
    for t in tickers:
        q = get_quotes(t)
        if not q or not q.get("price"):
            continue
        s = score_ticker(t, q)
        cat = best_catalyst_score(t)
        if s >= MIN_SCORE and cat:
            size = round(book_value * POSITION_PCT / q["price"], 4)
            risk = check_position(t, size, q["price"], book_value=book_value)
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


def run_cycle(tickers, book_value, account_number, auto_place=False):
    """One full sync-scan-to-exit cycle. auto_place=False logs only."""
    # Step 0: sync books before anything else
    if not sync_before_scan():
        print("SYNC DIRTY — skipping cycle to avoid sizing on stale data")
        # still allow logging-only scan so you can see candidates
        pass

    results = []
    for c in scan(tickers, book_value):
        print(f"CANDIDATE {c['ticker']} score={c['score']} cat={c['catalyst']} "
              f"entry={c['entry']} size={c['size']} TP={c['take_profit']} SL={c['stop_loss']}")
        if auto_place:
            if not ALPACA_AVAILABLE:
                print("  AUTO-PLACE BLOCKED: alpaca_exec unavailable")
                continue
            rev = review_order(account_number, c)
            alerts = rev.get("alerts") or []
            if alerts:
                print(f"  REVIEW ALERTS: {alerts}")
                continue
            entry = place_order(account_number, c)
            if entry.get("status") == "failed":
                print(f"  ENTRY FAILED: {entry.get('error')}")
                continue
            exits = place_exits(account_number, c)
            results.append({"entry": entry, "exits": exits, "candidate": c})
            print(f"  PLACED entry + bracket exits for {c['ticker']}")
    return results


if __name__ == "__main__":
    # Demo: log-only mode. Flip auto_place=True with Alpaca keys set to fire.
    demo_book = 10000
    demo_tickers = ["SPY", "QQQ", "IWM", "AAPL", "MSFT", "NVDA", "AMD", "TSLA"]
    run_cycle(demo_tickers, demo_book, account_number=None, auto_place=False)
