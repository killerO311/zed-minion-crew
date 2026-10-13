"""Zed Minion Crew — Scoring Engine

One score, zero approvals. Catalyst 40, liquidity 30, tape 30.
Clear 70 → auto-size at 1% of book and execute.
Below 70 → nothing. Zed sees the log after the fact.

Now wired to data_feed.py: pull a live quote, score it, log the result.
"""

from dataclasses import dataclass

from data_feed import DataFeed, Quote


@dataclass
class Setup:
    ticker: str
    catalyst_score: float   # 0-40
    liquidity_score: float  # 0-30
    tape_score: float       # 0-30

    @property
    def total(self) -> float:
        return self.catalyst_score + self.liquidity_score + self.tape_score

    @property
    def passes(self) -> bool:
        return self.total >= 70


def rank_setups(setups: list[Setup]) -> list[Setup]:
    """Return passing setups sorted by score, highest first."""
    return sorted([s for s in setups if s.passes], key=lambda s: s.total, reverse=True)


def size_position(score: float, book_value: float) -> float:
    """Top scores auto-size at 1% of the book."""
    if score < 70:
        return 0.0
    return 0.01 * book_value


# --- Filters (all three must pass or the name is skipped) ---

def filter_liquidity(avg_daily_volume: float, spread_bps: float) -> bool:
    return avg_daily_volume >= 1_000_000 and spread_bps <= 20


def filter_news_velocity(hours_since_catalyst: float) -> bool:
    return hours_since_catalyst <= 48


def filter_tape(higher_lows: bool, volume_shrinking: bool) -> bool:
    return higher_lows and volume_shrinking


# --- Live scoring: feed → score → log ---

def score_from_quote(q: Quote,
                     catalyst_score: float,
                     spread_bps: float = 10.0,
                     higher_lows: bool = True,
                     volume_shrinking: bool = True,
                     hours_since_catalyst: float = 24.0) -> Setup | None:
    """Score one ticker from a live quote. Returns None if any filter fails."""
    if not filter_liquidity(q.avg_volume_20, spread_bps):
        return None
    if not filter_news_velocity(hours_since_catalyst):
        return None
    if not filter_tape(higher_lows, volume_shrinking):
        return None

    # Liquidity sub-score: volume above 1M helps, tight spread helps
    liq = min(30.0, (q.avg_volume_20 / 1_000_000) * 10 + max(0, 20 - spread_bps))
    # Tape sub-score: RSI in 40-70 band is healthy momentum, not exhausted
    tape = 15.0
    if q.rsi_14 is not None:
        if 40 <= q.rsi_14 <= 70:
            tape += 10
        elif q.rsi_14 > 80:
            tape -= 5  # overbought bleed risk
    if q.macd is not None and q.macd_signal is not None and q.macd > q.macd_signal:
        tape += 5
    tape = min(30.0, tape)

    return Setup(q.ticker, catalyst_score, round(liq, 1), round(tape, 1))


def run_scan(tickers: list[str],
             catalyst_scores: dict[str, float],
             book_value: float = 100_000.0) -> list[Setup]:
    """Full loop: feed quotes → score → rank → size."""
    feed = DataFeed()
    setups: list[Setup] = []
    for t in tickers:
        try:
            q = feed.get_quote(t)
        except Exception as e:
            print(f"{t}: feed error — {e}")
            continue
        cat = catalyst_scores.get(t, 20.0)
        s = score_from_quote(q, cat)
        if s is None:
            print(f"{t}: filtered out (liquidity/news/tape)")
        else:
            setups.append(s)
            print(f"{s.ticker}: {s.total:.0f} — size ${size_position(s.total, book_value):,.0f} "
                  f"(price ${q.price:.2f}, RSI {q.rsi_14}, MACD {q.macd})")
    return rank_setups(setups)


if __name__ == "__main__":
    # Demo with manual catalyst scores — swap for a news feed later
    demo_catalysts = {
        "BMBL": 35,   # arb spread + volume
        "SPCX": 30,   # thesis, not a scalp
        "FRMI": 20,   # financing story, no revenue
        "SNAP": 25,   # momentum scalp, already ran
        "IREN": 22,
        "NUAI": 18,
    }
    winners = run_scan(list(demo_catalysts.keys()), demo_catalysts)
    print("---")
    if winners:
        for s in winners:
            print(f"PASS {s.ticker}: {s.total:.0f}")
    else:
        print("No setups cleared 70 today.")
