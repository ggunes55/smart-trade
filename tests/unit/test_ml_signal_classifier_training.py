import os
import sys
import random

import numpy as np
import pytest

# Proje kökünü PYTHONPATH'e ekle
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))

from analysis.ml_signal_classifier import MLSignalClassifier, SKLEARN_AVAILABLE


@pytest.mark.skipif(not SKLEARN_AVAILABLE, reason="scikit-learn not available")
def test_ml_signal_classifier_can_train_and_predict():
    """
    MLSignalClassifier'ın temel eğitim ve tahmin akışını doğrular.

    - Sentetik trade verisi üretir (hem kazanan hem kaybeden işlemler)
    - train() çağrısından sonra is_trained True olmalı
    - predict_signal_quality() makul bir sözlük döndürmeli
    """
    random.seed(42)
    np.random.seed(42)

    # 1) Sentetik trade verisi oluştur (pozitif/negatif karlar)
    historical_trades = []
    for i in range(80):
        # Yarım kazanan, yarım kaybeden olacak şekilde kar yüzdeleri
        if i % 2 == 0:
            profit_pct = random.uniform(3.0, 15.0)  # kazanan
        else:
            profit_pct = random.uniform(-8.0, 1.0)  # kaybeden/nötr

        features = {
            "rsi": random.uniform(20, 80),
            "macd": random.uniform(-2, 2),
            "adx": random.uniform(5, 40),
            "volume_ratio": random.uniform(0.5, 3.0),
            "trend_score": random.uniform(20, 90),
            "atr_percent": random.uniform(0.5, 5.0),
            "volatility": random.uniform(10, 80),
        }

        historical_trades.append({"profit_pct": profit_pct, "features": features})

    # 2) Sınıflandırıcıyı başlat ve eğit
    classifier = MLSignalClassifier()
    assert classifier.model is not None, "Model instance should be created when sklearn is available"

    classifier.train(historical_trades)
    assert classifier.is_trained, "Classifier should be marked as trained after train()"

    # 3) Basit bir tahmin yap ve dönen sözlüğü doğrula
    sample_features = historical_trades[0]["features"]
    result = classifier.predict_signal_quality(sample_features)

    assert isinstance(result, dict)
    assert "prediction" in result
    assert "confidence" in result
    assert "probability" in result

    # Confidence 0–1 aralığında, probability 0–100 aralığında olmalı
    assert 0.0 <= result["confidence"] <= 1.0
    assert 0.0 <= result["probability"] <= 100.0

