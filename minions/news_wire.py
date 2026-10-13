"""Bot 4 — News Wire

Pulls breaking headlines from free RSS feeds, detects catalyst keywords,
scores catalyst strength 0-40, and hands the score to scoring_engine.py.

Sources: Google News RSS (no key), Yahoo Finance news per ticker.
No paid APIs. If a feed is down, that ticker just scores lower.
"""

from __future__ import annotations

import logging
import re
import xml.etree.ElementTree as ET
from dataclasses import dataclass, field
from datetime import datetime, timezone, timedelta
from email.utils import parsedate_to_datetime
from typing import Any
from urllib.parse import quote_plus
from urllib.request import Request, urlopen

logger = logging.getLogger(__name__)

# --- Catalyst keyword banks: each hit adds weight ---

BULLISH_TERMS = {
    "contract": 8, "award": 8, "partnership": 7, "acquisition": 9,
    "merger": 9, "buyback": 6, "dividend increase": 6, "upgrade": 5,
    "beat": 7, "raised guidance": 8, "FDA approval": 10,
    "earnings beat": 8, "record revenue": 7, "new product": 5,
    "expansion": 4, "spin-off": 6, "tender offer": 9,
}

BEARISH_TERMS = {
    "downgrade": -6, "miss": -7, "lawsuit": -6, "investigation": -7,
    "bankruptcy": -10, "delisting": -10, "offering": -4,
    "dilution": -5, "guidance cut": -8, "recall": -7,
    "SEC": -5, "fraud": -9, "restatement": -8,
}

MACRO_TERMS = {
    "CPI": 3, "inflation": 3, "Fed": 3, "rate cut": 5,
    "rate hike": -4, "jobs report": 3, "GDP": 3,
}


@dataclass
class Catalyst:
    ticker: str
    headline: str
    source: str
    minutes_ago: int
    score: float  # 0-40
    direction: str  # bullish / bearish / mixed
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))


def _fetch_rss(url: str, timeout: int = 10) -> list[dict[str, Any]]:
    """Fetch and parse an RSS/Atom feed. Returns list of {title, published, link}."""
    try:
        req = Request(url, headers={"User-Agent": "zed-minion-crew/0.1"})
        with urlopen(req, timeout=timeout) as resp:
            raw = resp.read()
        root = ET.fromstring(raw)
        items = []
        # RSS 2.0
        for item in root.iter("item"):
            title = (item.findtext("title") or "").strip()
            pub = item.findtext("pubDate") or ""
            link = (item.findtext("link") or "").strip()
            items.append({"title": title, "published": pub, "link": link})
        # Atom fallback
        if not items:
            for entry in root.iter("entry"):
                title = (entry.findtext("title") or "").strip()
                pub = entry.findtext("published") or entry.findtext("updated") or ""
                link_el = entry.find("link")
                link = link_el.get("href", "") if link_el is not None else ""
                items.append({"title": title, "published": pub, "link": link})
        return items
    except Exception as e:
        logger.warning("RSS fetch failed for %s: %s", url, e)
        return []


def _minutes_ago(pub_str: str) -> int:
    """Convert an RSS pubDate string to minutes ago. 999 if unparseable."""
    if not pub_str:
        return 999
    try:
        dt = parsedate_to_datetime(pub_str)
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return max(0, int((datetime.now(timezone.utc) - dt).total_seconds() / 60))
    except Exception:
        return 999


def _score_headline(text: str) -> tuple[float, str]:
    """Score one headline. Returns (score 0-40, direction)."""
    lower = text.lower()
    bull = sum(w for term, w in BULLISH_TERMS.items() if term in lower)
    bear = sum(abs(w) for term, w in BEARISH_TERMS.items() if term in lower)
    macro = sum(w for term, w in MACRO_TERMS.items() if term.lower() in lower)

    raw = bull - bear + macro
    # Cap at 40
    score = max(0.0, min(40.0, raw))
    if bull > bear:
        direction = "bullish"
    elif bear > bull:
        direction = "bearish"
    else:
        direction = "mixed"
    return score, direction


class NewsWire:
    """Bot 4. Scans free RSS feeds for catalyst headlines per ticker."""

    GOOGLE_NEWS_URL = (
        "https://news.google.com/rss/search?q={query}&hl=en-US&gl=US&ceid=US:en"
    )
    YAHOO_NEWS_URL = "https://feeds.finance.yahoo.com/rss/2.0/headline?s={ticker}&region=US&lang=en-US"

    def __init__(self, window_minutes: int = 60):
        self._window = window_minutes

    def scan_ticker(self, ticker: str) -> list[Catalyst]:
        """Scan Google News + Yahoo Finance RSS for one ticker."""
        ticker = ticker.upper().strip()
        results: list[Catalyst] = []

        # Google News broad query
        g_url = self.GOOGLE_NEWS_URL.format(query=quote_plus(ticker))
        for item in _fetch_rss(g_url):
            mins = _minutes_ago(item["published"])
            if mins > self._window:
                continue
            score, direction = _score_headline(item["title"])
            if score > 0:
                results.append(Catalyst(ticker, item["title"], "google_news",
                                        mins, score, direction))

        # Yahoo Finance per-ticker feed
        y_url = self.YAHOO_NEWS_URL.format(ticker=ticker)
        for item in _fetch_rss(y_url):
            mins = _minutes_ago(item["published"])
            if mins > self._window:
                continue
            score, direction = _score_headline(item["title"])
            if score > 0:
                results.append(Catalyst(ticker, item["title"], "yahoo_finance",
                                        mins, score, direction))

        # Deduplicate by headline text
        seen: set[str] = set()
        deduped: list[Catalyst] = []
        for c in results:
            key = c.headline.lower().strip()
            if key not in seen:
                seen.add(key)
                deduped.append(c)
        return deduped

    def scan_many(self, tickers: list[str]) -> dict[str, list[Catalyst]]:
        return {t: self.scan_ticker(t) for t in tickers}

    def best_catalyst_score(self, ticker: str) -> float:
        """Return the single highest catalyst score for a ticker (0-40)."""
        cats = self.scan_ticker(ticker)
        if not cats:
            return 0.0
        return max(c.score for c in cats)


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    wire = NewsWire(window_minutes=180)  # 3-hour window for demo
    for sym in ["SPCX", "BMBL", "SNAP", "IREN", "NUAI", "FRMI"]:
        cats = wire.scan_ticker(sym)
        if cats:
            top = max(cats, key=lambda c: c.score)
            print(f"{sym}: best catalyst {top.score:.0f} ({top.direction}) — {top.headline[:90]}")
        else:
            print(f"{sym}: no catalyst headlines in window")
