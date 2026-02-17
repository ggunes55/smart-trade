# -*- coding: utf-8 -*-
"""
FAZA 1 ML Classifier Training & Verification Script

Amaç:
- Backtest sırasında TradeCollector ile toplanan işlemleri kullanarak
  MLSignalClassifier modelini eğitmek
- Basit doğrulama (accuracy, F1, AUC-ROC) metriklerini hesaplamak

Kullanım:
    python train_ml_faza1_from_trades.py

Önkoşul:
- Backtest'ler çalıştırılmış ve data_cache/ml_training_data.csv içinde
  yeterli sayıda trade kaydı oluşmuş olmalı.
"""

import logging
import os
import sys
from pathlib import Path

import numpy as np
import pandas as pd

from sklearn.metrics import accuracy_score, f1_score, roc_auc_score

# Proje kök dizinini PYTHONPATH'e ekle
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from analysis.trade_collector import TradeCollector
from analysis.ml_signal_classifier import MLSignalClassifier


logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)


def load_trades_from_csv() -> pd.DataFrame:
    """
    TradeCollector'ın yazdığı CSV'den eğitim verisini yükle.
    """
    csv_path = Path("data_cache/ml_training_data.csv")
    if not csv_path.exists():
        logger.error(f"❌ Eğitim verisi bulunamadı: {csv_path}")
        return pd.DataFrame()

    df = pd.read_csv(csv_path)
    if df.empty:
        logger.error(f"❌ Eğitim dosyası boş: {csv_path}")
    else:
        logger.info(f"✅ {csv_path} yüklendi ({len(df)} satır)")
    return df


def train_and_validate_faza1_classifier() -> bool:
    """
    FAZA 1 MLSignalClassifier'ı TradeCollector verisiyle eğit ve doğrula.
    """
    logger.info("=" * 80)
    logger.info("🚀 FAZA 1: MLSignalClassifier Training & Verification")
    logger.info("=" * 80)

    # 1) Veriyi yükle
    df = load_trades_from_csv()
    if df.empty:
        return False

    # TradeCollector.load_data formatına dönüştür (profit_pct + features dict)
    historical_trades = []
    required_cols = [
        "profit_pct",
        "rsi",
        "macd",
        "adx",
        "volume_ratio",
        "trend_score",
        "atr_percent",
        "volatility",
    ]

    missing = [c for c in required_cols if c not in df.columns]
    if missing:
        logger.error(f"❌ Eksik sütunlar: {missing}")
        return False

    for _, row in df.iterrows():
        historical_trades.append(
            {
                "profit_pct": float(row["profit_pct"]),
                "features": {
                    "rsi": float(row["rsi"]),
                    "macd": float(row["macd"]),
                    "adx": float(row["adx"]),
                    "volume_ratio": float(row["volume_ratio"]),
                    "trend_score": float(row["trend_score"]),
                    "atr_percent": float(row["atr_percent"]),
                    "volatility": float(row["volatility"]),
                },
            }
        )

    if len(historical_trades) < 50:
        logger.warning(f"⚠️ Eğitim için çok az trade var: {len(historical_trades)} (min 50 önerilir)")

    # 2) Modeli oluştur ve eğit
    classifier = MLSignalClassifier()
    if classifier.model is None:
        logger.error("❌ scikit-learn bulunamadı veya MLSignalClassifier başlatılamadı.")
        return False

    logger.info(f"[STEP 1] {len(historical_trades)} trade ile eğitim başlatılıyor...")
    classifier.train(historical_trades)

    if not classifier.is_trained:
        logger.error("❌ Eğitim başarısız oldu (is_trained=False)")
        return False

    logger.info("✅ Eğitim tamamlandı, doğrulama metrikleri hesaplanıyor... ")

    # 3) Basit doğrulama (train set üzerinde)
    X, y = classifier.prepare_training_data(historical_trades)
    if X.size == 0:
        logger.error("❌ Eğitim verisi boş görünüyor (X.size == 0)")
        return False

    try:
        X_scaled = classifier.scaler.transform(X)
        y_pred = classifier.model.predict(X_scaled)
        if hasattr(classifier.model, "predict_proba"):
            proba = classifier.model.predict_proba(X_scaled)[:, 1]
        else:
            # Olasılık yoksa 0/1 tahminleri üzerinden yaklaşık skor
            proba = y_pred.astype(float)

        acc = accuracy_score(y, y_pred)
        f1 = f1_score(y, y_pred, zero_division=0)
        try:
            auc = roc_auc_score(y, proba)
        except Exception:
            auc = 0.0

        logger.info(f"📊 Doğrulama Metrikleri (train set üzerinde):")
        logger.info(f"   - Accuracy : {acc:.3f}")
        logger.info(f"   - F1-score : {f1:.3f}")
        logger.info(f"   - AUC-ROC  : {auc:.3f}")

    except Exception as e:
        logger.error(f"❌ Doğrulama metrikleri hesaplanamadı: {e}")
        return False

    logger.info("✅ FAZA 1 classifier başarıyla eğitildi ve doğrulandı.")
    logger.info(f"   Model yolu: {classifier.model_path}")
    return True


if __name__ == "__main__":
    success = train_and_validate_faza1_classifier()
    sys.exit(0 if success else 1)

