import requests
import xml.etree.ElementTree as ET

BULLISH = ["contract", "award", "upgrade", "beat", "raised", "partnership", "acquisition", "buyback", "dividend"]
BEARISH = ["downgrade", "lawsuit", "bankruptcy", "investigation", "fraud", "recall", "miss", "cut", "layoff"]

FEEDS = {
    "google_news": "https://news.google.com/rss/search?q={ticker}+stock&hl=en-US&gl=US&ceid=US:en-US",
    "yahoo": "https://feeds.finance.yahoo.com/rss/2.0/headline?s={ticker}&region=US&lang=en-US",
    "benzinga": "https://www.benzinga.com/feed/news?ticker={ticker}",
    "marketwatch": "https://feeds.marketwatch.com/marketwatch/realtimeheadlines/",
    "cnbc": "https://www.cnbc.com/id/100003114/device/rss/rss.html",
    "sec_edgar": "https://data.sec.gov/submissions/CIK{cik}.json",
    "motley_fool": "https://www.fool.com/feed/news/",
}


def fetch_feed(url, ticker=None):
    try:
        r = requests.get(url.format(ticker=ticker) if ticker else url, timeout=10,
                         headers={"User-Agent": "zed-minion-crew research@example.com"})
        if r.status_code == 200:
            return r.text
    except Exception:
        return None
    return None


def score_headlines(text, ticker):
    if not text:
        return 0
    score = 0
    low = text.lower()
    for kw in BULLISH:
        score += low.count(kw) * 2
    for kw in BEARISH:
        score += low.count(kw) * -3
    if ticker and ticker.lower() in low:
        score += 1
    return max(0, min(score, 40))


def best_catalyst_score(ticker):
    best = 0
    for name, url in FEEDS.items():
        text = fetch_feed(url, ticker)
        s = score_headlines(text, ticker)
        if s > best:
            best = s
    return best


if __name__ == "__main__":
    for t in ["AAPL", "MSFT", "NVDA"]:
        print(t, best_catalyst_score(t))
