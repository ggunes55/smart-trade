# 🚀 FAZA 2 Başlangıç - Advanced ML & Dynamic Adaptation

**Tarih**: 12 Şubat 2026  
**Versiyon**: 3.3.2  
**Durum**: 🟡 IN_PROGRESS  

---

## 📋 FAZA 2 Nedir?

FAZA 1 ile mevcut analiz modüllerini entegre ederek signal kalitesini artırdık.  
**FAZA 2 amacı**: Sistem kendini öğrenerek ve uyarlayarak **otomatik gelişim** sağlamak.

### Hedefler
- **ML Model Eğitimi**: Backtest verilerine dayalı ML modeli eğitmek
- **Parametreleri Dinamik Optimizasyon**: Piyasa koşullarına göre ağırlıkları otomatik ayarlamak
- **Portfolio-Level Optimizasyon**: Tüm pozisyonlar için en iyi risk/reward oranı

---

## 🎯 FAZA 2 Task Listesi

### Task 2.1: ML Training Pipeline Oluştur
**Dosya**: `analysis/ml_training_pipeline.py`  
**Saati**: 6 saat  
**Kritiklik**: CRITICAL  

**Açıklama**:
- Backtest sonuçlarından train/test dataset oluştur
- Feature engineering (teknik gösterge, pattern, volatilite, vb.)
- Model eğitme (XGBoost, LightGBM, Random Forest)
- Model validasyonu ve cross-validation

**Inputs**:
- `backtest/backtester.py` çıktısı (historical trades)
- OHLCV verisi
- Teknik göstergeler

**Outputs**:
- Eğitilmiş `.pkl` model dosyası
- Feature importance raporu
- Model accuracy metrikleri (Precision, Recall, F1)

---

### Task 2.2: Genetic Algorithm Parameter Optimization
**Dosya**: `analysis/parameter_optimizer.py`  
**Saati**: 8 saat  
**Kritiklik**: HIGH  

**Açıklama**:
- Integration Engine'in ağırlıklarını optimize et (0.25, 0.25, 0.30, 0.20)
- Piyasa rejimi bazında farklı ağırlık setleri oluştur
- Backtest loop ile fitness evaluation yap
- Genetic algorithm ile en iyi kombinasyonu bul

**Parametre Setleri**:
```python
# Şu anda SABIT:
{
    "base_signal": 0.25,
    "confirmation": 0.25,
    "ml_confidence": 0.30,
    "entry_timing": 0.20
}

# FAZA 2 sonrası DINAMIK:
market_regimes = {
    "strong_uptrend": {"base": 0.20, "conf": 0.25, "ml": 0.35, "entry": 0.20},
    "weak_trend": {"base": 0.30, "conf": 0.30, "ml": 0.25, "entry": 0.15},
    "sideways": {"base": 0.25, "conf": 0.35, "ml": 0.25, "entry": 0.15},
}
```

---

### Task 2.3: Backtest to ML Training Loop
**Dosya**: `train_ml_model.py`  
**Saati**: 4 saat  
**Kritiklik**: HIGH  

**Açıklama**:
- Backtest çalıştır → Sonuçları topla
- Başarılı/başarısız işlemleri label'le
- Features extract et
- ML modeli eğit

**Workflow**:
```
1. Historical data oku (BIST 100, NASDAQ, vb.)
2. Backtest çalıştır
3. Trade sonuçlarını veritabanına kaydet
   ├─ Win trades → Label: 1 (başarılı)
   └─ Loss trades → Label: 0 (başarısız)
4. Features oluştur ve normalize et
5. 80/20 train/test split
6. Model eğit
7. Performance metrikleri hesapla
```

---

### Task 2.4: Portfolio-Level Optimization
**Dosya**: `risk/portfolio_optimizer.py`  
**Saati**: 6 saat  
**Kritiklik**: MEDIUM  

**Açıklama**:
- Tek sembol analizi → Portfolio analizi
- Position sizing (her işlem için en uygun miktar)
- Risk parity (tüm pozisyonlar eşit risk taşısın)
- Correlation matrix → Diversifikasyon

---

## 📊 FAZA 2 Beklenen Sonuçlar

### Önce (FAZA 1)
```
Signal Accuracy:        65% → 85%
False Positive Rate:    35% → 15%
Win Rate (Backtest):    48% → 58%
```

### Sonra (FAZA 2)
```
Signal Accuracy:        85% → 92%+ (ML model ile)
False Positive Rate:    15% → 8%
Win Rate (Backtest):    58% → 70%+
Sharpe Ratio:           0.8 → 1.5+
```

---

## 🔧 Başlamadan Önce Kontrol Et

- [ ] Backtest sonuçları kaydediliyor mu? (`backtest/backtester.py`)
- [ ] Trade verisi doğru format mı? (symbol, entry, exit, profit, vb.)
- [ ] Yeterli historical data var mı? (minimum 6 ay)
- [ ] Feature engineering modülleri mevcut mi? (`analysis/*.py`)

---

## 📁 Yaratılacak Dosyalar

### Yeni
- `analysis/ml_training_pipeline.py` (300+ lines)
- `risk/portfolio_optimizer.py` (250+ lines)
- `data_cache/ml_training_data.csv` (historical labeled data)
- `models/signal_predictor_v1.pkl` (eğitilmiş ML model)

### Güncellenecek
- `train_ml_model.py` (parametreler)
- `analysis/parameter_optimizer.py` (genetic algorithm)
- `scanner/symbol_analyzer.py` (dynamic weights)

---

## 🚦 FAZA 2 Başlangıç Adımları

### Adım 1: ML Training Pipeline Oluştur (6 saat)
```python
# analysis/ml_training_pipeline.py
class MLTrainingPipeline:
    def __init__(self, historical_trades_df):
        self.trades = historical_trades_df
        self.features = None
        self.model = None
    
    def prepare_data(self):
        # Dataset'i train/test'e böl
        pass
    
    def extract_features(self):
        # Technical indicators'dan features oluştur
        pass
    
    def train_model(self):
        # XGBoost/LightGBM eğitimi
        pass
    
    def evaluate(self):
        # Precision, Recall, F1 hesapla
        pass
```

### Adım 2: Parameter Optimizer'ı Kur (8 saat)
```python
# analysis/parameter_optimizer.py
class GeneticAlgorithmOptimizer:
    def __init__(self, cfg):
        self.population = []  # Weight combinations
        self.fitness_scores = []
    
    def create_population(self):
        # Random weight combinations oluştur
        pass
    
    def evaluate_fitness(self, weights):
        # Backtest çalıştır, win rate'i return et
        pass
    
    def evolve(self, generations=50):
        # Selection, crossover, mutation
        pass
```

### Adım 3: Training Loop Kur (4 saat)
```python
# train_ml_model.py (FAZA 2 versiyonu)
def train_full_pipeline():
    # 1. Backtest verisi topla
    backtest_results = run_backtest_on_historical_data()
    
    # 2. ML model eğit
    ml_pipeline = MLTrainingPipeline(backtest_results)
    model = ml_pipeline.train_model()
    
    # 3. Parametreleri optimize et
    optimizer = GeneticAlgorithmOptimizer(cfg)
    best_weights = optimizer.evolve(generations=100)
    
    # 4. En iyi modeli kaydet
    save_model(model)
    save_weights(best_weights)
```

---

## 📈 Success Metrics

### ML Model Başarısı
- Accuracy: >85%
- Precision: >80% (false positive düşük)
- Recall: >75% (false negative düşük)
- AUC-ROC: >0.85

### Parameter Optimization
- Backtest win rate: +15% artış
- Sharpe ratio: >1.2
- Max drawdown: <20%

### Portfolio Optimization
- Diversification index: >0.7
- Risk-adjusted return: +25%

---

## ⏰ Timeline

```
12-20 Şub: ML Training Pipeline (Task 2.1)
20-28 Şub: Parameter Optimization (Task 2.2)
28-01 Mart: Backtest Loop (Task 2.3)
01-15 Mart: Portfolio Optimization (Task 2.4)
15-28 Mart: Testing & Validation
```

---

## 🔗 İlişkili Dosyalar

- [FAZA1_RELEASE_NOTES.md](FAZA1_RELEASE_NOTES.md) - Önceki faz detayları
- [DEVELOPMENT_ROADMAP.json](DEVELOPMENT_ROADMAP.json) - Tam roadmap
- [train_ml_model.py](train_ml_model.py) - ML training script
- [backtest/backtester.py](backtest/backtester.py) - Backtest engine

---

**Status**: ✅ FAZA 2 Hazırlandı  
**Next Step**: Task 2.1'i başlat (ML Training Pipeline)

