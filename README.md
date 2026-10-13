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

## Minion Roles

- Bot 1 — Market Scout: live quotes, volume, catalysts before open.
- Bot 2 — Research: deep dives on flagged names — debt, shorts, catalysts.
- Bot 3 — Risk: watches positions, flags broken theses and stops.
- Bot 4 — News Wire: CPI, earnings, Fed, anything moving the tape inside the hour.

I hold the loop: assign, verify, kill anything unverified. Travis is the human in the loop — the one who says go.

## Stack

TradingAgents thinks. NautilusTrader executes and logs. OpenAlgo bridges to Robinhood.

## Warning

None of these are turnkey. You're assembling, not installing.

## Next Steps

1. Clone TradingAgents: https://github.com/TauricResearch/TradingAgents
2. Wire NautilusTrader as the execution backend.
3. Connect OpenAlgo to Robinhood.
4. Backtest the scoring engine before any live capital.
