# 🚀 Advanced Crypto Intraday Trading System

Gelişmiş yapay zeka destekli kripto para intraday trading sistemi. Demo modda çalışır, gerçek API anahtarları ile canlı veri çekebilir (paper trading).

## ✨ Özellikler

### 📊 Teknik Analiz (20+ İndikatör)
- **Trend**: EMA, VWAP, Supertrend, Ichimoku Cloud, ADX
- **Momentum**: RSI, Stochastic RSI, MACD (divergence detection), CCI
- **Volatilite**: ATR, Bollinger Bands (squeeze detection), Keltner Channels
- **Hacim**: Volume Delta, CVD, Order Book Imbalance

### 🎯 Sinyal Üretimi
- Ağırlıklı skorlama sistemi (7 bileşen)
- Güven skoru hesaplama (A/B/C/D derecelendirme)
- Risk/Reward oranı analizi
- Sinyal tipleri: Breakout, Pullback, Reversal, Continuation

### 🛡️ Risk Yönetimi
- Kelly Criterion pozisyon boyutlandırma
- ATR tabanlı stop loss
- Trailing stop ve breakeven logic
- Kill-switch (5% günlük kayıp)
- Korelasyon takibi
- Maksimum 3 eşzamanlı işlem

### 📈 Performans Takibi
- Sharpe ve Sortino oranları
- Drawdown takibi
- Kazanma oranı analizi
- Günlük performans metrikleri

### 🎨 Modern Dashboard
- Real-time veri gösterimi
- Dark mode tasarım
- Otomatik yenileme (10 saniye)
- Responsive tasarım

## 🚀 Hızlı Başlangıç

### 1. Kurulum

```bash
cd /Users/emircanuysal/Desktop/crypto
./setup.sh
```

Veya manuel kurulum:

```bash
# Virtual environment oluştur
python3 -m venv venv
source venv/bin/activate

# Bağımlılıkları yükle
pip install -r requirements.txt

# Docker servislerini başlat
docker-compose up -d postgres redis

# Veritabanını başlat
python3 -c "from src.database.connection import init_db; init_db()"
```

### 2. Yapılandırma

`.env` dosyasını düzenleyin:

```bash
# Demo mod için (API anahtarı gerekmez)
ENABLE_PAPER_TRADING=true

# Gerçek veri için (opsiyonel)
BINANCE_API_KEY=your_api_key
BINANCE_API_SECRET=your_api_secret
```

### 3. Çalıştırma

```bash
source venv/bin/activate
python main.py
```

### 4. Erişim

- **Dashboard**: http://localhost:8000
- **API Docs**: http://localhost:8000/docs
- **Grafana**: http://localhost:3000
- **Prometheus**: http://localhost:9090

## 📁 Proje Yapısı

```
crypto/
├── src/
│   ├── config/          # Ayarlar ve sabitler
│   ├── data/            # Exchange client ve veri yönetimi
│   ├── database/        # ORM modelleri ve bağlantı
│   ├── indicators/      # Teknik indikatörler
│   ├── signals/         # Sinyal üretimi ve skorlama
│   ├── risk/            # Risk yönetimi
│   ├── execution/       # İşlem yürütme
│   ├── analytics/       # Performans metrikleri
│   ├── api/             # FastAPI uygulaması
│   └── utils/           # Yardımcı araçlar
├── static/              # Frontend dashboard
├── monitoring/          # Prometheus/Grafana config
├── main.py             # Ana giriş noktası
├── docker-compose.yml  # Docker orchestration
└── requirements.txt    # Python bağımlılıkları
```

## 🎯 Kullanım

### API Endpoints

| Endpoint | Method | Açıklama |
|----------|--------|----------|
| `/` | GET | Dashboard |
| `/status` | GET | Sistem durumu |
| `/bot/start` | POST | Botu başlat |
| `/bot/stop` | POST | Botu durdur |
| `/positions` | GET | Açık pozisyonlar |
| `/trades` | GET | İşlem geçmişi |
| `/signals` | GET | Son sinyaller |
| `/performance` | GET | Performans metrikleri |

### Örnek API Kullanımı

```python
import requests

# Sistem durumunu kontrol et
response = requests.get('http://localhost:8000/status')
print(response.json())

# Açık pozisyonları görüntüle
positions = requests.get('http://localhost:8000/positions')
print(positions.json())
```

## ⚙️ Yapılandırma

### Risk Parametreleri

```bash
# .env dosyasında
RISK_PER_TRADE_PCT=1.0          # İşlem başına risk %1
MAX_LEVERAGE=3                   # Maksimum kaldıraç 3x
MAX_DAILY_LOSS_PCT=5.0          # Günlük kayıp limiti %5
MAX_CONCURRENT_TRADES=3          # Maksimum eşzamanlı işlem
CONFIDENCE_THRESHOLD=75.0        # Minimum güven skoru %75
```

### Trading Parametreleri

```bash
TRADING_PAIRS=BTC/USDT,ETH/USDT
TIMEFRAMES=1m,5m,15m
MIN_RISK_REWARD_RATIO=2.5
```

## 📊 Monitoring

### Prometheus Metrikleri

Sistem otomatik olarak şu metrikleri toplar:
- İşlem sayısı
- Kazanma oranı
- P&L
- Açık pozisyon sayısı
- API yanıt süreleri

### Grafana Dashboard

1. http://localhost:3000 adresine gidin
2. Varsayılan kullanıcı: `admin` / `admin`
3. Dashboard'ları import edin

## 🔒 Güvenlik

### Paper Trading

Sistem varsayılan olarak **paper trading** modunda çalışır:
- Gerçek para riski YOK
- Gerçek işlem yapılmaz
- Tüm işlemler simüle edilir

### Canlı Trading İçin

> ⚠️ **UYARI**: Canlı trading son derece risklidir!

1. En az 1 hafta paper trading yapın
2. Kazanma oranını doğrulayın (>45%)
3. Risk yönetimini test edin
4. Minimum sermaye ile başlayın ($100-500)
5. İlk 24 saat sürekli izleyin

```bash
# .env dosyasında
ENABLE_PAPER_TRADING=false  # Dikkatli kullanın!
```

## 🐛 Sorun Giderme

### Docker Servisleri Başlamıyor

```bash
docker-compose down
docker-compose up -d
```

### Veritabanı Hatası

```bash
docker-compose restart postgres
python3 -c "from src.database.connection import init_db; init_db()"
```

### Port Zaten Kullanımda

```bash
# 8000 portunu kullanan process'i bul
lsof -i :8000
# Process'i sonlandır
kill -9 <PID>
```

## 📈 Performans Beklentileri

### Gerçekçi Hedefler

- **Profesyonel**: 3-5% günlük getiri
- **Yüksek Risk**: 10-15% günlük getiri
- **Kumar Bölgesi**: 20%+ günlük getiri ⚠️

### Önemli Metrikler

- **Kazanma Oranı**: >45%
- **Profit Factor**: >1.5
- **Sharpe Ratio**: >1.0
- **Max Drawdown**: <20%

## 🛠️ Geliştirme

### Yeni İndikatör Ekleme

```python
# src/indicators/custom.py
def my_indicator(df: pd.DataFrame) -> pd.Series:
    # İndikatör hesaplama
    return result
```

### Yeni Sinyal Tipi Ekleme

```python
# src/signals/signal_generator.py içinde
def detect_my_signal(self, df: pd.DataFrame) -> bool:
    # Sinyal mantığı
    return signal_detected
```

## 📚 Dokümantasyon

- [QUICKSTART.md](QUICKSTART.md) - Detaylı kurulum rehberi
- [API Docs](http://localhost:8000/docs) - Swagger UI
- [Walkthrough](walkthrough.md) - Sistem geliştirme süreci

## ⚠️ Yasal Uyarı

> Bu yazılım eğitim amaçlıdır. Kripto para ticareti son derece risklidir. Tüm sermayenizi kaybedebilirsiniz. Sadece kaybetmeyi göze alabileceğiniz para ile işlem yapın. Geçmiş performans gelecek sonuçları garanti etmez.

## 🤝 Katkıda Bulunma

1. Fork yapın
2. Feature branch oluşturun (`git checkout -b feature/amazing`)
3. Commit yapın (`git commit -m 'Add amazing feature'`)
4. Push yapın (`git push origin feature/amazing`)
5. Pull Request açın

## 📄 Lisans

MIT License - Detaylar için LICENSE dosyasına bakın.

## 📞 Destek

Sorularınız için:
- GitHub Issues
- Email: support@example.com

---

**🎮 Demo Modda Çalışıyor - Güvenle Test Edin!**
