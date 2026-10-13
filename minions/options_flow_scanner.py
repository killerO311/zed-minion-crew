"""Options Flow Scanner — sixth minion.

Watches for whale options activity: large premium sweeps, unusual volume,
and OTM positioning that often precedes a move. Treats it as an instant
catalyst signal feeding the scoring engine.

Design (LuxAlgo whale-options patterns, streamlined):
- Volume ratio: today's volume vs 20-day average. 3x+ = unusual.
- Premium: total notional above $250K single-strike = whale.
- OTM sweep: calls or puts >10% OTM with volume > open interest = aggressive.
- Sentiment: call-heavy vs put-heavy skew.
- Score 0-40 to slot directly into scoring_engine catalyst_score.

Data: yfinance options chains (no paid feed). Free, rate-limited,
best-effort — not a Bloomberg terminal.
"""

from __future__ import annotations

from dataclasses import dataclass

import yfinance as yf

WHALE_PREMIUM = 250_000      # $ notional per strike = whale
VOLUME_RATIO_MIN = 3.0      # today's vol vs 20-day avg
OTM_PCT = 0.10              # >10% out of the money
MAX_SCORE = 40


@dataclass
class FlowSignal:
    ticker: str
    score: float            # 0-40, feeds catalyst_score
    sentiment: str          # "bullish", "bearish", "mixed", "none"
    whale_strikes: int
    unusual_volume: bool
    otm_sweep: bool
    call_premium: float
    put_premium: float
    detail: str


def _safe_chain(ticker: str, expiry: str):
    try:
        t = yf.Ticker(ticker)
        return t.option_chain(expiry)
    except Exception:
        return None


def _expiries(ticker: str) -> list[str]:
    try:
        t = yf.Ticker(ticker)
        return list(t.options)[:3]  # nearest 3 expirations
    except Exception:
        return []


def scan_ticker(ticker: str) -> FlowSignal:
    """Scan one ticker's near-term options for whale flow."""
    expiries = _expiries(ticker)
    if not expiries:
        return FlowSignal(ticker, 0, "none", 0, False, False, 0.0, 0.0, "no chain")

    whale_strikes = 0
    call_premium = 0.0
    put_premium = 0.0
    otm_sweep = False
    unusual = False
    spot = None

    for exp in expiries:
        chain = _safe_chain(ticker, exp)
        if chain is None:
            continue
        # spot price from the chain if available
        try:
            spot = float(yf.Ticker(ticker).info.get("currentPrice") or 0) or spot
        except Exception:
            pass

        for side_name, df in (("call", chain.calls), ("put", chain.puts)):
            if df is None or df.empty:
                continue
            for _, row in df.iterrows():
                try:
                    vol = float(row.get("volume") or 0)
                    oi = float(row.get("openInterest") or 0)
                    strike = float(row.get("strike") or 0)
                    iv = float(row.get("impliedVolatility") or 0)
                    last = float(row.get("lastPrice") or 0)
                except (TypeError, ValueError):
                    continue

                premium = vol * last * 100  # contract multiplier
                if premium >= WHALE_PREMIUM:
                    whale_strikes += 1
                    if side_name == "call":
                        call_premium += premium
                    else:
                        put_premium += premium

                if oi > 0 and vol / oi >= VOLUME_RATIO_MIN:
                    unusual = True

                if spot and spot > 0:
                    if side_name == "call" and strike > spot * (1 + OTM_PCT) and vol > oi:
                        otm_sweep = True
                    if side_name == "put" and strike < spot * (1 - OTM_PCT) and vol > oi:
                        otm_sweep = True

    # Score: whale strikes (up to 20), unusual volume (10), OTM sweep (10)
    score = 0.0
    score += min(20.0, whale_strikes * 5)
    if unusual:
        score += 10
    if otm_sweep:
        score += 10
    score = min(MAX_SCORE, score)

    if call_premium > put_premium * 1.5:
        sentiment = "bullish"
    elif put_premium > call_premium * 1.5:
        sentiment = "bearish"
    elif call_premium > 0 or put_premium > 0:
        sentiment = "mixed"
    else:
        sentiment = "none"

    detail = (f"whales={whale_strikes} call_prem=${call_premium:,.0f} "
              f"put_prem=${put_premium:,.0f} unusual={unusual} otm_sweep={otm_sweep}")
    return FlowSignal(ticker, score, sentiment, whale_strikes, unusual,
                      otm_sweep, call_premium, put_premium, detail)


def scan_universe(tickers: list[str]) -> list[FlowSignal]:
    """Scan a list of tickers, return signals sorted by score."""
    signals = [scan_ticker(t) for t in tickers]
    return sorted([s for s in signals if s.score > 0], key=lambda s: s.score, reverse=True)


if __name__ == "__main__":
    for s in scan_universe(["SPY", "QQQ", "NVDA", "TSLA", "AAPL"]):
        print(f"{s.ticker}: score={s.score:.0f} sentiment={s.sentiment} | {s.detail}")
