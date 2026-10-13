"""Zed Minion Crew — Scoring Engine

One score, zero approvals. Catalyst 40, liquidity 30, tape 30.
Clear 70 → auto-size at 1% of book and execute.
Below 70 → nothing. Zed sees the log after the fact.
"""

from dataclasses import dataclass


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


if __name__ == "__main__":
    demo = [
        Setup("BMBL", 35, 28, 27),   # arb spread + volume
        Setup("SPCX", 30, 25, 20),   # thesis, not a scalp
        Setup("FRMI", 20, 22, 18),   # financing story, no revenue
        Setup("SNAP", 25, 27, 24),   # momentum scalp, already ran
    ]
    for s in rank_setups(demo):
        print(f"{s.ticker}: {s.total:.0f} — size ${size_position(s.total, 100_000):,.0f}")
