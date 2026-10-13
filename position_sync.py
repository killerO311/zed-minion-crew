"""Robinhood-to-Alpaca position sync.

Pulls Robinhood positions via robin_stocks, maps against Alpaca's paper book,
and flags discrepancies: wrong shares, stale prices, missing tickers, extra
positions on either side. Logs to sync_report.txt instead of silently breaking
sizing. Scalper calls sync_before_scan() at the top of every cycle.
"""

import json
import os
from datetime import datetime, timezone

REPORT_PATH = os.path.join(os.path.dirname(__file__) or ".", "sync_report.txt")


def _rh_positions():
    """Fetch Robinhood positions. Returns dict keyed by ticker or error dict."""
    try:
        import robin_stocks.robinhood as rh
    except ImportError:
        return {"_error": "robin_stocks not installed"}

    try:
        # robin_stocks needs a login; try without credentials (token may persist)
        positions = rh.get_open_stock_positions()
        out = {}
        for p in positions:
            try:
                instrument = rh.get_instrument_by_url(p["instrument"])
                ticker = instrument["symbol"]
                qty = float(p["quantity"])
                avg = float(p.get("average_buy_price") or 0)
                out[ticker] = {"qty": qty, "avg_price": avg}
            except Exception:
                continue
        return out
    except Exception as e:
        return {"_error": f"robinhood fetch failed: {e}"}


def _alpaca_positions():
    """Fetch Alpaca positions via alpaca_exec."""
    try:
        from alpaca_exec import get_positions
        return get_positions()
    except Exception as e:
        return {"_error": f"alpaca fetch failed: {e}"}


def sync():
    """Compare Robinhood vs Alpaca. Return report dict."""
    rh = _rh_positions()
    ap = _alpaca_positions()
    report = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "robinhood": rh,
        "alpaca": ap,
        "discrepancies": [],
    }

    if "_error" in rh:
        report["discrepancies"].append(f"ROBINHOOD: {rh['_error']}")
    if "_error" in ap:
        report["discrepancies"].append(f"ALPACA: {ap['_error']}")

    rh_keys = {k for k in rh if not k.startswith("_")}
    ap_keys = {k for k in ap if not k.startswith("_")}

    for t in sorted(rh_keys | ap_keys):
        r = rh.get(t)
        a = ap.get(t)
        if r and not a:
            report["discrepancies"].append(
                f"MISSING IN ALPACA: {t} qty={r['qty']} @ {r['avg_price']}"
            )
        elif a and not r:
            report["discrepancies"].append(
                f"MISSING IN ROBINHOOD: {t} qty={a['qty']} @ {a['avg_entry']}"
            )
        elif r and a:
            if abs(r["qty"] - a["qty"]) > 1e-6:
                report["discrepancies"].append(
                    f"QTY MISMATCH {t}: RH={r['qty']} ALPACA={a['qty']}"
                )
            # price sanity: if avg prices diverge > 5%, flag it
            if r["avg_price"] > 0 and a["avg_entry"] > 0:
                pct = abs(r["avg_price"] - a["avg_entry"]) / r["avg_price"]
                if pct > 0.05:
                    report["discrepancies"].append(
                        f"PRICE DRIFT {t}: RH={r['avg_price']:.2f} ALPACA={a['avg_entry']:.2f} ({pct:.1%})"
                    )

    _write_report(report)
    return report


def _write_report(report):
    """Append report to sync_report.txt."""
    line = json.dumps(report) + "\n"
    try:
        with open(REPORT_PATH, "a") as f:
            f.write(line)
    except Exception:
        pass  # never let reporting break the bot


def sync_before_scan():
    """Called by scalper at top of every cycle. Returns True if clean."""
    report = sync()
    if report["discrepancies"]:
        print("SYNC DISCREPANCIES:")
        for d in report["discrepancies"]:
            print(f"  {d}")
        return False
    print("SYNC CLEAN — Robinhood and Alpaca books match")
    return True


if __name__ == "__main__":
    r = sync()
    print(json.dumps(r, indent=2))
