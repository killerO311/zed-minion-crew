from data_feed import get_quotes
from minions.news_wire import best_catalyst_score


def scan(tickers):
    """Live market snapshot: quotes + catalyst scores for a ticker list."""
    out = []
    for t in tickers:
        q = get_quotes(t)
        if q:
            out.append({"ticker": t, "quote": q, "catalyst": best_catalyst_score(t)})
    return out


if __name__ == "__main__":
    for row in scan(["SPY", "QQQ", "IWM"]):
        print(row)
