"""Live market data feed for the Zed minion crew.

Pulls quotes, volume, and technicals from Yahoo Finance via yfinance.
Wraps the feed so scoring_engine.py can score any ticker without
knowing where the numbers came from.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any

import yfinance as yf
import pandas as pd

logger = logging.getLogger(__name__)


@dataclass
class Quote:
    ticker: str
    price: float
    prev_close: float
    change_pct: float
    volume: int
    avg_volume_20: float
    day_high: float
    day_low: float
    fifty_two_week_high: float
    fifty_two_week_low: float
    rsi_14: float | None = None
    macd: float | None = None
    macd_signal: float | None = None
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))


class DataFeed:
    """Yahoo Finance-backed feed. One call per ticker, cached per session."""

    def __init__(self, cache_ttl_seconds: int = 60):
        self._cache: dict[str, tuple[datetime, Quote]] = {}
        self._ttl = cache_ttl_seconds

    def get_quote(self, ticker: str) -> Quote:
        ticker = ticker.upper().strip()
        now = datetime.now(timezone.utc)
        if ticker in self._cache:
            ts, q = self._cache[ticker]
            if (now - ts).total_seconds() < self._ttl:
                return q

        t = yf.Ticker(ticker)
        info = t.info or {}
        hist = t.history(period="3mo", interval="1d")

        if hist.empty:
            raise ValueError(f"No price history returned for {ticker}")

        last = hist.iloc[-1]
        prev = hist.iloc[-2] if len(hist) > 1 else last
        price = float(last["Close"])
        prev_close = float(prev["Close"])
        change_pct = (price - prev_close) / prev_close * 100 if prev_close else 0.0

        vol = int(last["Volume"]) if not pd.isna(last["Volume"]) else 0
        avg_vol = float(hist["Volume"].tail(20).mean()) if len(hist) >= 20 else float(vol)

        rsi = self._rsi(hist["Close"], 14)
        macd_line, signal_line = self._macd(hist["Close"])

        q = Quote(
            ticker=ticker,
            price=price,
            prev_close=prev_close,
            change_pct=round(change_pct, 2),
            volume=vol,
            avg_volume_20=round(avg_vol, 0),
            day_high=float(last["High"]),
            day_low=float(last["Low"]),
            fifty_two_week_high=float(info.get("fiftyTwoWeekHigh") or hist["High"].max()),
            fifty_two_week_low=float(info.get("fiftyTwoWeekLow") or hist["Low"].min()),
            rsi_14=round(rsi, 2) if rsi is not None else None,
            macd=round(macd_line, 4) if macd_line is not None else None,
            macd_signal=round(signal_line, 4) if signal_line is not None else None,
        )
        self._cache[ticker] = (now, q)
        return q

    def get_quotes(self, tickers: list[str]) -> dict[str, Quote]:
        return {t: self.get_quote(t) for t in tickers}

    @staticmethod
    def _rsi(series: pd.Series, period: int = 14) -> float | None:
        if len(series) < period + 1:
            return None
        delta = series.diff()
        gain = delta.clip(lower=0).rolling(period).mean()
        loss = (-delta.clip(upper=0)).rolling(period).mean()
        rs = gain / loss.replace(0, pd.NA)
        rsi = 100 - (100 / (1 + rs))
        val = rsi.iloc[-1]
        return float(val) if not pd.isna(val) else None

    @staticmethod
    def _macd(series: pd.Series, fast: int = 12, slow: int = 26, signal: int = 9) -> tuple[float | None, float | None]:
        if len(series) < slow + signal:
            return None, None
        ema_fast = series.ewm(span=fast, adjust=False).mean()
        ema_slow = series.ewm(span=slow, adjust=False).mean()
        macd_line = ema_fast - ema_slow
        signal_line = macd_line.ewm(span=signal, adjust=False).mean()
        return float(macd_line.iloc[-1]), float(signal_line.iloc[-1])


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    feed = DataFeed()
    for sym in ["SPCX", "BMBL", "FRMI", "SNAP", "IREN", "NUAI"]:
        try:
            q = feed.get_quote(sym)
            print(f"{q.ticker}: ${q.price:.2f} ({q.change_pct:+.2f}%) vol={q.volume:,} "
                  f"RSI={q.rsi_14} MACD={q.macd}")
        except Exception as e:
            print(f"{sym}: ERROR {e}")
