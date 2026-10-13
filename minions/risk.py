MAX_POSITION_PCT = 0.05      # 5% of book max per name
MAX_DAILY_LOSS_PCT = 0.02   # kill switch: 2% of book per day


def check_position(ticker, size, price, book_value=10000, daily_loss=0.0):
    """Approve or reject a proposed position."""
    position_value = size * price
    if position_value > book_value * MAX_POSITION_PCT:
        return {"approved": False, "reason": f"position exceeds {MAX_POSITION_PCT:.0%} of book"}
    if daily_loss >= book_value * MAX_DAILY_LOSS_PCT:
        return {"approved": False, "reason": "daily loss kill switch tripped"}
    if price and price > 0:
        pass
    return {"approved": True, "reason": "ok"}


if __name__ == "__main__":
    print(check_position("TEST", 10, 50, book_value=10000, daily_loss=0))
    print(check_position("TEST", 10, 50, book_value=10000, daily_loss=250))
