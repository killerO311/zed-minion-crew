# Zed Minion Crew

TradingAgents-based multi-agent trading system.

## Architecture

- **Brain (TradingAgents)**: Multi-agent LangGraph framework simulating a trading firm — fundamental analyst, sentiment analyst, technical analyst, trader, risk manager. LLM agents debate to a decision. Works with Grok, OpenAI, Anthropic, Gemini, DeepSeek, Ollama.
- **Spine (NautilusTrader)**: Production-grade execution layer. Rust core, Python strategy API. Same code runs in backtest and live. Nanosecond event resolution, durable event logging.
- **Glue (OpenAlgo)**: Self-hosted broker bridge. Python Flask + React, 36 broker plugins, no-code strategy builder, risk management built in, process isolation per strategy.

## Scoring Engine

One score, zero approvals. Catalyst worth up to 40 points, liquidity 30, tape 30. Anything clearing 70 auto-sizes at 1% of the book and executes. Below 70, nothing. Zed sees the log after the fact, not before.

## Filters

1. **Liquidity**: Average daily volume north of 1 million shares, tight spread.
2. **News velocity**: Something broke in the last 48 hours the market hasn't fully digested.
3. **Tape turning**: Price making higher lows on shrinking volume.

Miss any one and Zed sits on his hands — but the checklist ranks, it doesn't gate.

## Minion Roles & Fork Sources

| Minion | File | Fork Source | What It Does |
|--------|------|-------------|-------------|
| Bot 1 — Market Scout | `minions/market_scout.py` | Calls `data_feed.py` + `news_wire.py` | Live quotes, volume, catalysts before open |
| Bot 2 — Research | `minions/research.py` | Calls `data_feed.py` + `news_wire.py` | Deep dives on flagged names — debt, shorts, catalysts |
| Bot 3 — Risk | `minions/risk.py` | Native logic + position-size cap + daily loss kill switch | Watches positions, flags broken theses and stops |
| Bot 4 — News Wire | `minions/news_wire.py` | 7 sources: Benzinga, MarketWatch, CNBC, Motley Fool, SEC EDGAR + Google News/Yahoo RSS | CPI, earnings, Fed, anything moving the tape inside the hour |
| Bot 5 — Scalper | `minions/scalper_bot.py` | LumiBot strategy patterns (github.com/Lumiwealth/lumibot) | Dedicated intraday scalper: score gate at 70, 1% position sizing, 0.8% take-profit, 0.4% stop, Robinhood marketable-limit entry with GTC brackets |

## External Forks (reference, not wired in)

- **LumiBot** — github.com/killerO311/lumibot — stock trading with AI agent runtime (researcher, bull, bear, portfolio manager). 12 brokers incl. Schwab, Tradier, Alpaca, IBKR.
- **hftbacktest** — github.com/killerO311/hftbacktest — tick-level backtesting with queue position and latency modeling. Live on Binance/Bybit (untested per authors).
- **Public-Portfolio-Challenge** — github.com/killerO311/Public-Portfolio-Challenge (austin-starks) — Fable 5 momentum options bot, +20% in 10 weeks, full campaign log.
- **temple-stuart-accounting** — github.com/killerO311/temple-stuart-accounting (Temple-Stuart) — $400 Robinhood bot grew to $1,200 over 8 months.
- **claude-trading-desk** — github.com/killerO311/claude-trading-desk (aabrole) — free end-to-end stack: build, backtest, paper-trade Claude bots. 67 files, plugin with strategy/oracle/paper-trading/dashboard skills, opening-range-breakout example.

## Stack

TradingAgents thinks. NautilusTrader executes and logs. OpenAlgo bridges to Robinhood.

## Warning

None of these are turnkey. You're assembling, not installing. Backtest before any live capital touches the scalper's `auto_place` flag.

## Next Steps

1. Wire `scalper_bot.py` `auto_place=True` with Zed's account number when ready for real orders.
2. Backtest the scoring engine on historical data before scaling position sizes.
3. Add a sixth minion: options flow scanner (unusual options activity as catalyst signal).
4. Connect the news wire's EDGAR feed to auto-flag 8-K filings as instant catalysts.
