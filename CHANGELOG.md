# Changelog

All notable changes to this project will be documented in this file.

## [v0.2.0] - Multi-Timeframe Analysis & Core Optimizations

### Added
- **Multi-Timeframe Analysis (MTF)**: `trading_bot.py` now fetches 1h macro trend data and passes it to the signal generator. 5m signals are automatically rejected if they strongly contradict the 1h macro trend.
- **Partial Take Profit**: Implemented risk management feature where 50% of a position is closed at `1:2 R/R` (ATR * 2) and the stop-loss is moved to breakeven (`entry_price`).
- **Volume Filter**: Added a strict volume filter that aborts signals if the 5-candle average volume drops beneath 70% of the historical average, protecting against false breakouts during illiquid periods.
- `CHANGELOG.md` file to track project version history.

### Changed
- **Async Optimizations**: Wrapped blocking API calls (`sentiment_client.get_fear_greed_index` and `news_client.get_latest_news`) in `asyncio.to_thread` to prevent the trading loop from locking up.
- **Database Sessions**: Refactored `models.py` to support `partial_tp_hit` state tracking and removed dead code columns.
- **Signal Weights**: Increased trend confirmation weight from 20% to 30% to compensate for the removal of on-chain data.
- Shortened and cleaned up the verbose English developer notes in `engine.py`.

### Removed
- **Dead Code**: Completely stripped all references and parameters related to `onchain_score` across the entirety of the project (bot loop, models, generator, constants) since the logic is not yet implemented.
- Removed local sync API calls from inside the `generate_signal` engine to centralize rate limiting.

---

## [v0.1.0] - Initial Release

### Added
- Modular architecture for crypto algorithmic trading bots.
- Core indicators (Trend, Momentum, Volatility, Volume, Advanced Math).
- Baseline execution, scoring engine, and SQLite database modeling. 
- Integrated backtest engine with simplified LONG/SHORT capital allocation and PnL tracking log.
