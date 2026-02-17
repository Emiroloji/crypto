# Changelog

## [0.1.0] - 2026-02-17

### ✨ İlk Sürüm - Temel Sistem

#### Eklenenler

**Altyapı**
- Docker orchestration (PostgreSQL, Redis, Prometheus, Grafana)
- FastAPI REST API
- Modern web dashboard (dark mode)
- Kapsamlı logging sistemi
- Redis caching katmanı

**Veri Toplama**
- Binance ve Bybit exchange client'ları
- Demo data generator (API anahtarı olmadan test)
- OHLCV veri toplama
- Order book tracking
- Funding rate monitoring
- Open interest tracking

**Teknik Analiz (20+ İndikatör)**
- **Trend**: EMA, VWAP, Supertrend, Ichimoku Cloud, ADX
- **Momentum**: RSI, Stochastic RSI, MACD (divergence detection), CCI
- **Volatilite**: ATR, Bollinger Bands (squeeze detection), Keltner Channels
- **Hacim**: Volume Delta, CVD, Order Book Imbalance

**Sinyal Sistemi**
- Ağırlıklı skorlama sistemi (7 bileşen)
- Güven skoru hesaplama (A/B/C/D)
- Risk/Reward analizi
- Sinyal tipleri: Breakout, Pullback, Reversal, Continuation

**Risk Yönetimi**
- Kelly Criterion pozisyon boyutlandırma
- ATR tabanlı stop loss
- Trailing stop ve breakeven
- Kill-switch (5% günlük kayıp)
- Korelasyon takibi
- Maksimum 3 eşzamanlı işlem limiti

**İşlem Yürütme**
- Tam otomatik trade executor
- Position management
- Paper trading modu
- Order tracking

**Performans Takibi**
- Sharpe ve Sortino oranları
- Drawdown hesaplama
- Günlük performans metrikleri
- Win rate tracking

**Dashboard & API**
- Modern, responsive web arayüzü
- Real-time veri gösterimi
- 12+ REST API endpoint
- Swagger UI dokümantasyonu

**Dokümantasyon**
- Kapsamlı README (Türkçe)
- QUICKSTART rehberi
- API dokümantasyonu
- Deployment scriptleri

#### Güvenlik
- Paper trading varsayılan olarak aktif
- Demo mode (API anahtarı gerekmez)
- Risk limitleri zorunlu
- Kill-switch mekanizması

#### Bilinen Sınırlamalar
- Sentiment analizi henüz entegre değil (opsiyonel)
- On-chain data tracking yok (opsiyonel)
- Backtesting engine yok (opsiyonel)
- Unit testler eksik (opsiyonel)

---

## Gelecek Sürümler

### [0.2.0] - Planlanan
- Sentiment analysis integration
- Backtesting engine
- Walk-forward optimization
- Advanced ML models

### [0.3.0] - Planlanan
- Mobile app
- Advanced alerting
- Multi-account support
- Cloud deployment templates
