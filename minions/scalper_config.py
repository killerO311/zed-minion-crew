# Scalper minion configuration
# Automation name: Scalper
# Schedule: daily 9:30 AM CT

WHALE_PREMIUM_MIN = 100_000      # loosened from 250K
WHALE_VOLUME_OI_RATIO = 2.0     # loosened from 3x
OTM_SWEEP_PCT = 10.0
SCORE_GATE = 70
POSITION_SIZE_PCT = 0.01        # 1% of book per name
TAKE_PROFIT_PCT = 0.008
STOP_LOSS_PCT = 0.004

TICKERS = ["SPY", "QQQ", "IWM", "AAPL", "MSFT", "NVDA", "TSLA", "AMD", "META", "AMZN"]

# Sentiment skew thresholds
CALL_HEAVY_RATIO = 1.5
PUT_HEAVY_RATIO = 0.67
