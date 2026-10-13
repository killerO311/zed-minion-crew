# Scalper Minion

Dedicated intraday scalper for stocks. Named "Scalper" in the Automations dashboard.

## Sources
- LumiBot (github.com/Lumiwealth/lumibot) — strategy patterns, broker loop
- hftbacktest (github.com/nkaz001/hftbacktest) — tick-level execution research
- options_flow_scanner.py — whale detection engine (LuxAlgo-inspired)

## Scan Logic
1. Pull options chains for nearest 3 expirations per ticker
2. Flag strikes with premium > $100K, volume >= 2x OI, OTM sweeps > 10%
3. Score 0-40: premium weight 15, volume/OI 10, OTM sweep 10, sentiment skew 5
4. Merge with data_feed quotes + news_wire catalyst scores in scoring_engine
5. Names clearing 70 auto-size at 1% of book

## Risk
- 5% max position cap (risk module)
- 2% max daily loss kill switch (risk module)
- 0.8% take-profit, 0.4% stop (scalper_bot.py)

## Automation
- Name: Scalper
- Cadence: daily 9:30 AM Central
- Mode: report-only, no auto-placement
- Notification: default (email + app)

## Upgrade path
- Wire real Robinhood SDK into scalper_bot.py (currently stub)
- Replace yfinance options with Unusual Whales or Cheddar Flow for institutional-grade flow
- Add paper-trading mode before flipping auto_place
