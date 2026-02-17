# 🚀 Swing Trade - Swing Hunter Ultimate v3.3.2

**Kurumsal Seviye Swing Trading Tarayıcı & Real-time Portfolio Analiz Platformu**

Swing-Trade, BIST (Borsa İstanbul), Global Piyasalar (NASDAQ, NYSE) ve Kripto Paralar için tasarlanmış profesyonel trading platformudur. **Self-learning AI**, **real-time WebSocket** ve **advanced portfolio optimization** ile birleştirilmiş güçlü swing trading sistem.

[![Python](https://img.shields.io/badge/Python-3.8%2B-blue)]()
[![PyQt5](https://img.shields.io/badge/GUI-PyQt5-green)]()
[![License](https://img.shields.io/badge/License-MIT-orange)]()
[![Version](https://img.shields.io/badge/Version-3.3.2-brightgreen)]()

---

## 📋 İçerik

1. [Özellikler](#özellikler)
2. [Kurulum](#kurulum)
3. [Hızlı Başlangıç](#hızlı-başlangıç)
4. [Modüller](#modüller)
5. [Konfigürasyon](#konfigürasyon)
6. [Kullanım Örnekleri](#kullanım-örnekleri)
7. [API Referansı](#api-referansı)
8. [Teknik Mimarı](#teknik-mimarı)
9. [Performans](#performans)
10. [Troubleshooting](#troubleshooting)

---

## ⭐ Özellikler

### 🎯 Core Trading Features

| Özellik | Açıklama | Durum |
|---------|----------|-------|
| **Multi-Exchange Support** | BIST, NASDAQ, NYSE, Kripto | ✅ Live |
| **Advanced Technical Analysis** | 20+ indikatör (EMA, RSI, MACD, ADX, vb.) | ✅ Live |
| **Market Regime Detection** | Bullish/Bearish/Ranging otomatik tanısı | ✅ Live |
| **Volatility Analysis** | Squeeze, Bands, ATR adaptive | ✅ Live |
| **Pattern Recognition** | Support/Resistance, Fibonacci, Divergence | ✅ Live |
| **Institutional Flow Detection** | Volume profiling, Smart Money traces | ✅ Live |
| **Real-time WebSocket** | tvDatafeed / yfinance canlı veri, Aç/Kes butonları | ✅ Live |

### 🧠 AI & Machine Learning

| Özellik | Açıklama | Durum |
|---------|----------|-------|
| **ML Signal Classification** | XGBoost/LightGBM with feature extraction | ✅ Live |
| **Genetic Algorithm Optimizer** | Win-rate based weight optimization | ✅ Live |
| **Self-Learning System** | Continuous backtest → ML → optimization loop | ✅ Live |
| **Portfolio Risk Management** | Kelly Criterion, Risk Parity, Correlation | ✅ Live |
| **Adaptive Parameters** | Market conditions'a göre oto-ayarlı | ✅ Live |

### 📊 Visualization & Analytics

| Özellik | Açıklama | Durum |
|---------|----------|-------|
| **Interactive Charts** | TradingView-style multi-timeframe | ✅ Live |
| **Live Price Ticker** | Canlı Fiyatlar sekmesi (dikey liste, Aç/Kes butonları) | ✅ Live |
| **Backtest Dashboard** | Trade analysis, P&L curves, metrics | ✅ Live |
| **Market Analysis** | Piyasa rejimi, trend, momentum görsel | ✅ Live |
| **ML Management UI** | Model training, validation, export | ✅ Live |

### 🔔 Notifications & Alerts

| Kanal | Açıklama | Durum |
|--------|----------|-------|
| **Toast Notifications** | In-app popups | ✅ Live |
| **Desktop Alerts** | Windows bildirim sistemi | ✅ Phase 3 |
| **Telegram Bot** | Custom bot API entegrasyonu | ⚙️ Config |
| **Email** | SMTP-based alerts | ⚙️ Config |
| **Smart Suggestions** | Error-based recommendations | ✅ Live |

### 🎨 User Interface

| Bileşen | Açıklama | Tabs |
|---------|----------|------|
| **Symbols Tab** | Sembol seçimi & filtering | 1 |
| **Results Tab** | Scan sonuçları & trade listesi | 2 |
| **Market Tab** | Piyasa analizi & regime | 3 |
| **Chart Tab** | Interactive PyQtGraph candlestick charts | 4 |
| **Backtest Tab** | Historical strategy testing | 5 |
| **Trade Analysis** | Trade-by-trade detaylı analiz | 6 |
| **Portfolio Tab** | Position tracking & P&L | 7 |
| **Watchlist Tab** | Real-time monitoring | 8 |
| **Score Distribution** | Signal distribution heatmap | 9 |
| **Risk Analysis** | Risk metrics & VAR | 10 |
| **ML Management** | Model training & versioning | 11 |
| **Settings** | Konfigürasyon & preferences | 12 |

---

## 📦 Kurulum

### Gereksinimler

```
Python 3.8+
PyQt5
pandas, numpy
scikit-learn
xgboost (opsiyonel)
tvDatafeed
talib (TA-Lib)
```

### Adım 1: Repository'i Clone Et

```bash
git clone https://github.com/yourusername/swing-trade.git
cd swing-trade
```

### Adım 2: Virtual Environment Oluştur

```bash
python -m venv venv
.\venv\Scripts\activate  # Windows
source venv/bin/activate  # Linux/Mac
```

### Adım 3: Bağımlılıkları Yükle

```bash
pip install -r requirements.txt
pip install -r requirements-dev.txt  # (Opsiyonel) Development tools
```

### Adım 4: TA-Lib Yükle (Önemli!)

TA-Lib kurulumu system-specific:

**Windows:**
```bash
pip install TA-Lib
```

**Linux:**
```bash
sudo apt-get install python3-dev libta-lib0 libta-lib-dev
pip install TA-Lib
```

**Mac:**
```bash
brew install ta-lib
pip install TA-Lib
```

### Adım 5: Uygulamayı Başlat

```bash
python run.py
```

---

## 🚀 Hızlı Başlangıç

### 1. İlk Tarama

```
1. Sembolleri Seç
   - "Symbols" tabında BIST, NASDAQ veya Kripto seçin
   - Örn: ASELS, GARAN, AKBNK, nvda, aapl

2. Piyasa Analizi Yap
   - "Market" tabında BIST piyasasının rejimini görün
   - Bullish/Bearish/Ranging durumunu kontrol et

3. Taramayı Başlat
   - "Run Scan" butonuna tıkla
   - Sistem tüm sembolleri analiz eder

4. Sonuçları Görüntüle
   - "Results" tabında sinyal puanlarını incele
   - Yüksek puanlı signalleri seç
```

### 2. Grafik Analiz

```
1. Sembollere Tıkla
   - Results'ta symbol'e çift tıkla

2. Grafiği Görüntüle
   - Interactive candlestick chart açılır
   - EMA, RSI, MACD indikatörleri görünür
```

### 3. Backtest Yap

```
1. Backtest Yapılandır
   - "Backtest" tabında sempol ve tarih aralığı seç
   - Stop loss, target, exit stratejisi belirle

2. Backtest Çalıştır
   - "Start Backtest" butonuna tıkla
   - Sistem tarihi test eder

3. Sonuçları Analiz Et
   - Win Rate, Total P&L, Sharpe Ratio görüntüle
   - Trade-by-trade detayları incele
```

### 4. Real-time WebSocket (Canlı Fiyatlar)

```
1. Sembol Seç
   - Sol panel "Hisseler" sekmesinde en az bir sembol seçili olsun

2. WebSocket Aç
   - "Canlı Fiyatlar" sekmesinde "🔌 WebSocket'i Aç" butonuna tıklayın
   - Veya tarama başlatıp bitirdikten sonra otomatik başlar
   - Bağlantı durumu (●) ve fiyat listesi yukarıdan aşağı kaydırılabilir

3. WebSocket Kapat
   - "WebSocket Bağlantısını Kes" ile manuel kapatma (ücretsiz tvDatafeed kısıtı için önerilir)

4. Veri Kaynağı (config)
   - swing_config.json → real_time.live_data_source: "tvdatafeed" veya "yfinance"
   - poll_interval_sec: 5, max_live_symbols: 30 (ücretsiz planda önerilir)
```

---

## 🏗️ Modüller

### Core Modules

#### `scanner/` - Tarama Motoru
```
swing_hunter.py          : Ana scanning engine
data_handler.py          : Veri işleme & caching
symbol_table.py          : Sembol & exchange yönetimi
ml_data_gen.py           : ML training verileri oluştur
```

#### `analysis/` - Teknik & Yapay Zeka Analiz
```
Technical Indicators:
├── beta.py              : Beta calculation
├── consolidation.py     : Consolidation detection
├── divergence.py        : Momentum divergence
├── entry_timing.py      : Optimal entry points
├── fibonacci.py         : Fibonacci levels
├── kalman_filter.py     : Noise filtering
├── market_condition.py  : Market analysis
├── market_regime_adapter.py : Regime detection
├── multi_timeframe.py   : Timeframe analysis
├── relative_strength.py : Relative strength
├── risk_metrics.py      : Risk calculations
├── signal_confirmation.py: Signal validation
├── support_resistance.py: S/R levels
├── swing_quality.py     : Signal quality score
├── trend_score.py       : Trend strength
├── volatility.py        : Volatility analysis

ML & Optimization:
├── ml_signal_classifier.py      : XGBoost classifier
├── ml_training_pipeline.py      : Training pipeline
├── integration_engine.py        : Signal integration
├── parameter_optimizer.py       : Genetic algorithm
```

#### `backtest/` - Backtesting Engine
```
backtester.py          : Realistic backtester
├── realistic_execution
├── precise_entry/exit
├── slippage modeling
├── partial exit support (T1/T2/T3 targets)
```

#### `risk/` - Risk Management
```
portfolio_optimizer.py  : Kelly Criterion, Risk Parity
position_sizing.py      : Capital allocation
correlation_analyzer.py : Diversification checks
```

#### `gui/` - User Interface (PyQt5)
```
main_window/
├── main_window.py      : Ana window container
├── websocket_handlers.py: Real-time handlers

tabs/
├── symbols_tab.py      : Sembol seçimi
├── results_tab.py      : Scan sonuçları
├── market_tab.py       : Piyasa analizi
├── chart_tab.py        : Interactive charts
├── backtest_tab.py     : Backtesting UI
├── trade_analysis_tab.py: Trade detayları
├── portfolio_tab.py    : Portfolio view
├── watchlist_tab.py    : Real-time watchlist
├── score_tab.py        : Signal distribution
├── risk_tab.py         : Risk metrics
├── ml_management_tab.py: Model management
├── settings_tab.py     : Configuration

widgets/
├── price_ticker.py     : Real-time price display
├── chart_widget.py     : TradingView-style charts
└── ...

workers/
├── websocket_worker.py : Real-time data worker
├── market_worker.py    : Market analysis worker
├── backtest_worker.py  : Backtest executor
└── ...

notifications/
├── notification_manager.py : Multi-channel alerts
```

### Data & Configuration

```
swing_config.json       : Ana configuration
data_cache/
├── ml_training_data.csv: ML training dataset
endexler/
├── BIST_100.csv        : BIST100 historical data
├── NASDAQ_100.csv      : Nasdaq historical data
└── ...
```

---

## ⚙️ Konfigürasyon

### swing_config.json Ana Sections

```json
{
  "exchanges": {
    "BIST": {
      "enabled": true,
      "min_volume": 100000,
      "price_precision": 2,
      "market_hours": "09:30-17:00"
    },
    "NASDAQ": {
      "enabled": true,
      "min_volume": 50000
    }
  },

  "scanner": {
    "default_timeframe": "1d",
    "lookback_periods": 252,
    "use_parallel_scan": true,
    "parallel_workers": 8
  },

  "indicators": {
    "ema_periods": [20, 50, 200],
    "rsi_period": 14,
    "macd_periods": [12, 26, 9],
    "adx_period": 14,
    "atr_period": 14
  },

  "websocket": {
    "enabled": true,
    "endpoint": "wss://data.tradingview.com/socket.io/",
    "update_interval_ms": 100,
    "use_tvdata": true
  },

  "real_time": {
    "enable_signal_triggers": true,
    "enable_portfolio_tracking": true,
    "signal_threshold_pct": 2.0,
    "notification_channels": {
      "toast": true,
      "desktop": true,
      "telegram": false,
      "email": false
    }
  },

  "backtest": {
    "default_capital": 50000,
    "commission_pct": 0.1,
    "slippage_pct": 0.05,
    "max_position_pct": 5.0
  },

  "ml": {
    "use_ml": true,
    "model_type": "xgboost",
    "train_split": 0.8,
    "validation_split": 0.1
  },

  "weights": {
    "technical_score": 0.25,
    "confidence_score": 0.25,
    "ml_score": 0.25,
    "entry_timing": 0.25
  }
}
```

### Telegram Konfigürasyonu (Opsiyonel)

```json
"telegram": {
  "enabled": true,
  "bot_token": "YOUR_BOT_TOKEN",
  "chat_id": "YOUR_CHAT_ID"
}
```

**Bot token almak:**
1. Telegram'da @BotFather'a yaz
2. /newbot komutunu gir
3. Bot adı ve username belirle
4. Token al ve config'e yapıştır

**Chat ID almak:**
1. @userinfobot veya @MissRose_bot ile chat aç
2. /start komutunu gir
3. Chat ID'yi kopyala

---

## 📚 Kullanım Örnekleri

### Örnek 1: Programmatic Tarama

```python
from scanner.swing_hunter import SwingHunterUltimate
from core.types import ScanConfig

# Configuration
config = ScanConfig(
    symbols=['ASELS', 'GARAN', 'AKBNK'],
    exchanges=['BIST'],
    timeframe='1d',
    min_score=60
)

# Scanner initialize
scanner = SwingHunterUltimate(config)

# Tarama yapı
results = scanner.scan()

# Sonuçları işle
for result in results:
    print(f"{result.symbol}: {result.total_score:.1f} ({result.signal_type})")
```

### Örnek 2: Backtest

```python
from backtest.backtester import RealisticBacktester

backtester = RealisticBacktester(
    symbol='ASELS',
    start_date='2025-01-01',
    end_date='2025-12-31',
    capital=50000,
    stop_loss_pct=2.0,
    target_pct=5.0
)

results = backtester.run()
print(f"Win Rate: {results.win_rate:.1f}%")
print(f"Total P&L: ₺{results.total_pnl:.2f}")
```

### Örnek 3: ML Model Eğitimi

```python
from analysis.ml_training_pipeline import MLTrainingPipeline

pipeline = MLTrainingPipeline(
    backtest_results=backtest_data,
    model_type='xgboost',
    train_split=0.8
)

model = pipeline.train()
accuracy = pipeline.evaluate()
print(f"Model Accuracy: {accuracy:.1f}%")
```

### Örnek 4: Real-time Signaling

```python
from gui.workers.websocket_worker import WebSocketWorker

worker = WebSocketWorker(['ASELS', 'GARAN'], config)
worker.price_updated.connect(on_price_update)
worker.signal_triggered.connect(on_signal)

worker.start()
```

---

## 🔌 API Referansı

### ScanConfig
```python
class ScanConfig:
    symbols: List[str]           # Tarama yapılacak semboller
    exchanges: List[str]         # BIST, NASDAQ, NYSE
    timeframe: str               # 1d, 1h, 15m, 5m, 1m
    lookback: int                # Periyot sayısı (default: 252)
    min_score: float             # Minimum sinyal puanı (0-100)
    market_regime: str           # bullish, bearish, ranging, auto
```

### ScanResult
```python
class ScanResult:
    symbol: str
    price: float
    technical_score: float       # 0-100
    confidence_score: float      # 0-100
    ml_score: float             # 0-100
    entry_timing: float         # 0-100
    total_score: float          # 0-100 (weighted sum)
    signal_type: str            # BUY, SELL, HOLD
    
    # Indicators
    ema20: float
    rsi14: float
    macd_signal: str
    adx_trend: str
```

### WebSocketWorker (pyqtSignals)
```python
worker = WebSocketWorker(symbols, config)

# Signals
worker.price_updated.connect(slot)        # (symbol, price, change%)
worker.signal_triggered.connect(slot)     # (signal_dict)
worker.portfolio_updated.connect(slot)    # (portfolio_state)
worker.connection_status.connect(slot)    # (is_connected: bool)
worker.error_occurred.connect(slot)       # (error_message: str)
```

---

## 🏛️ Teknik Mimarı

### System Architecture

```
┌─────────────────────────────────────────────────────┐
│                   GUI (PyQt5)                        │
│            Main Window (12 Tabs)                     │
├─────────────────────────────────────────────────────┤
│                                                      │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────┐  │
│  │   Workers    │  │  Themes &    │  │ State    │  │
│  │              │  │  Styling     │  │ Manager  │  │
│  │ - Market     │  │              │  │          │  │
│  │ - WebSocket  │  └──────────────┘  └──────────┘  │
│  │ - Backtest   │                                     │
│  │ - Watchlist  │                                     │
│  └──────────────┘                                     │
│                                                      │
├─────────────────────────────────────────────────────┤
│                  Core Modules                       │
│                                                      │
│  ┌────────────┐  ┌──────────┐  ┌──────────────┐   │
│  │  Scanner   │  │ Analysis │  │  Backtest    │   │
│  │            │  │          │  │              │   │
│  │ - Hunter   │  │ - Tech   │  │ - Realistic  │   │
│  │ - Data Mgr │  │ - ML     │  │ - Metrics    │   │
│  └────────────┘  │ - Integrate └──────────────┘   │
│                  │ Engine                           │
│                  └──────────┘                       │
│                                                      │
│  ┌──────────────┐  ┌──────────────────────┐        │
│  │   Risk Mgmt  │  │  Notifications       │        │
│  │              │  │                      │        │
│  │ - Optimizer  │  │ - Toast              │        │
│  │ - Position   │  │ - Desktop            │        │
│  │   Sizing     │  │ - Telegram (opt)     │        │
│  │ - Correlation│  │ - Email (opt)        │        │
│  └──────────────┘  └──────────────────────┘        │
│                                                      │
├─────────────────────────────────────────────────────┤
│         External Data Sources                       │
│                                                      │
│  ┌──────────────┐  ┌──────────────────┐            │
│  │  tvDatafeed  │  │  Local Data       │            │
│  │  (Real-time) │  │  (Historical)     │            │
│  └──────────────┘  └──────────────────┘            │
└─────────────────────────────────────────────────────┘
```

### Data Flow

```
User Input (Symbols, Config)
    ↓
Scanner Engine
    ↓
├→ Technical Analysis (20+ indicators)
│    ↓
│  Technical Score (0-100)
│
├→ Market Regime Detection
│    ↓
│  Regime-aware adjustment
│
├→ ML Classification
│    ↓
│  ML Score (0-100)
│
├→ Entry Timing Optimization
│    ↓
│  Entry Score (0-100)
│
└→ Integration Engine
    ↓
  Final Score (0-100) = weighted sum
    ↓
  Signal Generation (BUY/SELL)
    ↓
GUI Display & Notification
```

---

## 📊 Performans

### Tipik Sistem Performansı

| Metrik | 50 Sembol | 200 Sembol |
|--------|-----------|-----------|
| **Tarama Süresi** | 5-10 sn | 20-30 sn |
| **CPU Kullanımı** | 30-40% | 60-75% |
| **Memory** | 300-400 MB | 800-1000 MB |
| **Real-time Update** | 100ms | 100ms |
| **WebSocket Latency** | <1 sn | <1 sn |

### Optimization İpuçları

```python
# 1. Sembol sayısını azalt
config['scanner']['symbols'] = config['scanner']['symbols'][:50]

# 2. Parallelization'ı etkinleştir
config['scanner']['use_parallel_scan'] = True
config['scanner']['parallel_workers'] = 8

# 3. Lookback periyodunu kısalt
config['scanner']['lookback_periods'] = 100  # 252'den azalt

# 4. Cache'i kullan
config['cache_ttl_hours'] = 24

# 5. WebSocket update interval'ını artır
config['real_time']['update_interval_ms'] = 500  # 100'den artır
```

---

## 🐛 Troubleshooting

### Sık Karşılaşılan Sorunlar

#### 1. TA-Lib Import Hatası
```
Error: ModuleNotFoundError: No module named 'talib'
```

**Çözüm:**
```bash
pip uninstall TA-Lib
pip install TA-Lib  # Platform-specific version gerekli
```

#### 2. tvDatafeed Veri Hatası
```
Warning: tvDatafeed using nologin method
```

**Çözüm:** (Opsiyonel) TradingView hesabı ile login yap:
```python
tv = TvDatafeed(username='user', password='pass')
```

#### 3. GUI Render Hatası
```
Error: QApplication instance already exists
```

**Çözüm:** Önceki instance kapatıldığından emin ol:
```bash
pkill -f "python run.py"
python run.py
```

#### 4. WebSocket Connection Timeout
```
Error: WebSocket connection timeout
```

**Çözüm:** Fallback simülasyon moduna otomatik geçiş (normal):
```json
{
  "websocket": {
    "timeout_ms": 60000,
    "reconnect_attempts": 5,
    "reconnect_delay_ms": 5000
  }
}
```

#### 5. ML Model Training Başarısız
```
Error: ValueError: X must be 2D array
```

**Çözüm:** Training data formatını kontrol et:
```python
# Eğer insufficient data:
if len(trades) < 50:
    print("Training için minimum 50 trade gerekli")
```

### Debug Mode

```bash
# Debug logging'i etkinleştir
config['debug_mode'] = true
config['log_level'] = 'DEBUG'

# Çalıştır
python run.py 2>&1 | grep -i error
```

### Log Files

```
swing_hunter.log     : Main application logs
backtest_results/    : Backtest trade details
ml_models/          : Model saves & history
```

---

## 📞 İletişim & Destek

### Hata Raporu Gönder

1. [GitHub Issues](github.com/yourrepo/issues) aç
2. Error message'i al (`swing_hunter.log` dosyasından)
3. Konfigürasyon (sensitif bilgiler hariç)
4. Sembller ve tarih aralığı

### Özellik İsteği

Discussion bölümünde:
- Ne istediğini açıkla
- Kullanım senaryosunu belirt
- Beklenen benefit'i açıkla

### Community

- GitHub Discussions
- Email: support@swingtrade.dev
- Twitter: @SwingTradeAI

---

## 📄 Lisans

MIT License - Detaylar için [LICENSE](LICENSE) dosyasını oku.

---

## 🙏 İçindekiler

- **tvDatafeed** - Real-time veri
- **TA-Lib** - Technical indicators
- **XGBoost/scikit-learn** - Machine learning
- **PyQt5** - GUI framework
- Trading komityası & beta testers

---

## 📊 Roadmap

### Q1 2026 (Tamamlandı)
- [x] Phase 1: Integration Engine
- [x] Phase 2: ML & Optimization
- [x] Phase 3: Real-time WebSocket

### Q2 2026 (Planlanmış)
- [ ] Mobile App (iOS/Android)
- [ ] Advanced charting (TradingView Pro)
- [ ] API Gateway (REST/GraphQL)
- [ ] Cloud deployment

### Q3 2026+
- [ ] High-frequency trading support
- [ ] Multi-exchange arbitrage
- [ ] Distributed backtesting
- [ ] Enterprise features

---

**Son Güncelleme**: 12 Şubat 2026  
**Versiyon**: 3.3.2  
**Status**: 🟢 Production Ready
