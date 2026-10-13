"""Scalper Bot — fully automated intraday scalper for stocks.

Pipeline: scan → score → risk-check → review → place → monitor → exit.
- Score gate: 70+ via scoring_engine
- Catalyst required inside two weeks via news_wire
- Position size: 1% of book
- Take-profit 0.8%, stop-loss 0.4%
- Risk module enforces 5% max position and 2% daily-loss kill switch
- Broker: Robinhood equity orders (marketable limit at ask for immediate fill)
- Exits: take-profit limit + stop-market, both GTC
"""

import uuid

from data_feed import get_quotes
from scoring_engine import score_ticker
from minions.risk import check_position
from minions.news_wire import best_catalyst_score

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


def review_order(account_number, candidate):
    """Pre-trade review via Robinhood — surfaces buying power, PDT, halts."""
    from robinhood import review_equity_order  # injected at runtime
    return review_equity_order(
        account_number=account_number,
        symbol=candidate["ticker"],
        side="buy",
        type="limit",
        quantity=str(candidate["size"]),
        limit_price=str(candidate["entry"]),
        time_in_force="gfd",
    )


def place_order(account_number, candidate, ref_id=None):
    """Place the entry as a marketable limit at the ask."""
    from robinhood import place_equity_order  # injected at runtime
    return place_equity_order(
        account_number=account_number,
        symbol=candidate["ticker"],
        side="buy",
        type="limit",
        quantity=str(candidate["size"]),
        limit_price=str(candidate["entry"]),
        time_in_force="gfd",
        ref_id=ref_id or str(uuid.uuid4()),
    )


def place_exits(account_number, candidate, ref_id=None):
    """Bracket: take-profit limit sell + stop-market sell, both GTC."""
    from robinhood import place_equity_order  # injected at runtime
    rid = ref_id or str(uuid.uuid4())
    tp = place_equity_order(
        account_number=account_number,
        symbol=candidate["ticker"],
        side="sell",
        type="limit",
        quantity=str(candidate["size"]),
        limit_price=str(candidate["take_profit"]),
        time_in_force="gtc",
        ref_id=rid + "-tp",
    )
    sl = place_equity_order(
        account_number=account_number,
        symbol=candidate["ticker"],
        side="sell",
        type="stop_market",
        quantity=str(candidate["size"]),
        stop_price=str(candidate["stop_loss"]),
        time_in_force="gtc",
        ref_id=rid + "-sl",
    )
    return {"take_profit": tp, "stop_loss": sl}


def run_cycle(tickers, book_value, account_number, auto_place=False):
    """One full scan-to-exit cycle. auto_place=False logs only."""
    results = []
    for c in scan(tickers, book_value):
        print(f"CANDIDATE {c['ticker']} score={c['score']} cat={c['catalyst']} "
              f"entry={c['entry']} size={c['size']} TP={c['take_profit']} SL={c['stop_loss']}")
        if auto_place:
            rev = review_order(account_number, c)
            alerts = rev.get("order_checks") or rev.get("alerts") or []
            if alerts:
                print(f"  REVIEW ALERTS: {alerts}")
                continue
            entry = place_order(account_number, c)
            exits = place_exits(account_number, c)
            results.append({"entry": entry, "exits": exits, "candidate": c})
            print(f"  PLACED entry + bracket exits for {c['ticker']}")
    return results


if __name__ == "__main__":
    # Demo: log-only mode. Flip auto_place=True with a real account number to fire.
    demo_book = 10000
    demo_tickers = ["SPY", "QQQ", "IWM", "AAPL", "MSFT", "NVDA", "AMD", "TSLA"]
    run_cycle(demo_tickers, demo_book, account_number=None, auto_place=False)
