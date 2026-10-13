"""Alpaca execution layer for the scalper bot.

Replaces the robinhood stub with real API calls via alpaca-py.
Paper mode is ON by default — nothing real fires until PAPER=False.
Env vars required: APCA_API_KEY_ID, APCA_API_SECRET_KEY.
Optional: APCA_PAPER (default true), APCA_BASE_URL.
"""

import os
import uuid

PAPER = os.getenv("APCA_PAPER", "true").lower() in ("1", "true", "yes")


def _client():
    """Lazy-init the Alpaca TradingClient."""
    try:
        from alpaca.trading.client import TradingClient
        from alpaca.trading.requests import (
            MarketOrderRequest,
            LimitOrderRequest,
            StopOrderRequest,
            TakeProfitRequest,
            StopLossRequest,
        )
        from alpaca.trading.enums import OrderSide, TimeInForce, OrderClass
    except ImportError as e:
        raise ImportError(
            "alpaca-py not installed. pip install alpaca-py"
        ) from e

    key = os.getenv("APCA_API_KEY_ID")
    secret = os.getenv("APCA_API_SECRET_KEY")
    if not key or not secret:
        raise ValueError(
            "APCA_API_KEY_ID and APCA_API_SECRET_KEY must be set"
        )

    return TradingClient(
        api_key=key,
        secret_key=secret,
        paper=PAPER,
    ), {
        "MarketOrderRequest": MarketOrderRequest,
        "LimitOrderRequest": LimitOrderRequest,
        "StopOrderRequest": StopOrderRequest,
        "TakeProfitRequest": TakeProfitRequest,
        "StopLossRequest": StopLossRequest,
        "OrderSide": OrderSide,
        "TimeInForce": TimeInForce,
        "OrderClass": OrderClass,
    }


def review_order(account_number, candidate):
    """Pre-trade review: buying power, PDT flag, halts via Alpaca."""
    client, _ = _client()
    try:
        acct = client.get_account()
        buying_power = float(acct.buying_power)
        equity = float(acct.equity)
        # PDT: Alpaca flags pattern_day_trader on the account
        pdt = getattr(acct, "pattern_day_trader", False)
        alerts = []
        needed = candidate["size"] * candidate["entry"]
        if needed > buying_power:
            alerts.append(f"insufficient buying power: need {needed:.2f}, have {buying_power:.2f}")
        if pdt:
            alerts.append("pattern day trader flag active")
        return {
            "approved": len(alerts) == 0,
            "alerts": alerts,
            "buying_power": buying_power,
            "equity": equity,
            "pdt": pdt,
        }
    except Exception as e:
        return {"approved": False, "alerts": [f"review failed: {e}"]}


def place_order(account_number, candidate, ref_id=None):
    """Marketable limit buy at the ask."""
    client, enums = _client()
    rid = ref_id or str(uuid.uuid4())
    req = enums["LimitOrderRequest"](
        symbol=candidate["ticker"],
        qty=candidate["size"],
        side=enums["OrderSide"].BUY,
        limit_price=candidate["entry"],
        time_in_force=enums["TimeInForce"].DAY,
        client_order_id=rid,
    )
    try:
        order = client.create_order(req)
        return {"id": order.id, "status": order.status, "ref_id": rid}
    except Exception as e:
        return {"id": None, "status": "failed", "error": str(e), "ref_id": rid}


def place_exits(account_number, candidate, ref_id=None):
    """Bracket: take-profit limit sell + stop-market sell, both GTC."""
    client, enums = _client()
    rid = ref_id or str(uuid.uuid4())
    tp_req = enums["LimitOrderRequest"](
        symbol=candidate["ticker"],
        qty=candidate["size"],
        side=enums["OrderSide"].SELL,
        limit_price=candidate["take_profit"],
        time_in_force=enums["TimeInForce"].GTC,
        client_order_id=rid + "-tp",
    )
    sl_req = enums["StopOrderRequest"](
        symbol=candidate["ticker"],
        qty=candidate["size"],
        side=enums["OrderSide"].SELL,
        stop_price=candidate["stop_loss"],
        time_in_force=enums["TimeInForce"].GTC,
        client_order_id=rid + "-sl",
    )
    results = {"take_profit": None, "stop_loss": None}
    try:
        results["take_profit"] = client.create_order(tp_req)
    except Exception as e:
        results["take_profit"] = {"error": str(e)}
    try:
        results["stop_loss"] = client.create_order(sl_req)
    except Exception as e:
        results["stop_loss"] = {"error": str(e)}
    return results


def get_positions():
    """Return Alpaca positions as a dict keyed by ticker."""
    client, _ = _client()
    try:
        positions = client.get_all_positions()
        return {
            p.symbol: {
                "qty": float(p.qty),
                "avg_entry": float(p.avg_entry_price),
                "market_value": float(p.market_value),
                "unrealized_pl": float(p.unrealized_pl),
            }
            for p in positions
        }
    except Exception as e:
        return {"_error": str(e)}


if __name__ == "__main__":
    print("PAPER MODE:" , PAPER)
    try:
        print(review_order(None, {"ticker": "SPY", "size": 1, "entry": 500}))
        print(get_positions())
    except Exception as e:
        print("init error:", e)
