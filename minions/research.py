from data_feed import get_quotes
from minions.news_wire import best_catalyst_score


def deep_dive(ticker):
    """Valuation fields from the feed plus catalyst context from news wire."""
    q = get_quotes(ticker)
    cat = best_catalyst_score(ticker)
    if not q:
        return None
    return {
        "ticker": ticker,
        "price": q.get("price"),
        "volume": q.get("volume"),
        "rsi": q.get("rsi"),
        "macd": q.get("macd"),
        "range_52w": q.get("range_52w"),
        "catalyst_score": cat,
    }


if __name__ == "__main__":
    print(deep_dive("AAPL"))
