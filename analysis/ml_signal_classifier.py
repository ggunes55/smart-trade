# -*- coding: utf-8 -*-
"""
ML Signal Classifier - Sinyal Kalitesini Tahmin Et
Random Forest algoritması kullanarak sinyallerin başarı olasılığını tahmin eder.
"""
import logging
import numpy as np
import pickle
import os
from typing import Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)

# Opsiyonel bağımlılıklar
try:
    from sklearn.ensemble import RandomForestClassifier
    from sklearn.preprocessing import StandardScaler
    SKLEARN_AVAILABLE = True
except ImportError:
    logger.warning("scikit-learn not found. ML features will be disabled.")
    SKLEARN_AVAILABLE = False

class MLSignalClassifier:
    """
    Random Forest tabanlı sinyal sınıflandırıcı.
    Geçmiş işlemlerden öğrenerek yeni sinyalleri puanlar.
    """
    
    def __init__(self, model_path: str = "models/signal_classifier.pkl"):
        self.model_path = model_path
        self.model = None
        self.scaler = None
        self.is_trained = False
        
        if SKLEARN_AVAILABLE:
            # ✅ OPTİMİZASYON: Paralel eğitim için n_jobs=-1 eklendi
            self.model = RandomForestClassifier(
                n_estimators=100, 
                max_depth=10, 
                random_state=42,
                n_jobs=-1  # Tüm CPU çekirdeklerini kullan
            )
            self.scaler = StandardScaler()
            self._load_model()
            
    def _load_model(self):
        """Varsa eğitilmiş modeli yükle"""
        if os.path.exists(self.model_path):
            try:
                with open(self.model_path, 'rb') as f:
                    saved_data = pickle.load(f)
                    self.model = saved_data['model']
                    self.scaler = saved_data['scaler']
                    self.is_trained = True
                logger.info(f"ML Model loaded from {self.model_path}")
            except Exception as e:
                logger.error(f"Error loading ML model: {e}")
                
    def save_model(self):
        """Modeli kaydet"""
        if not self.is_trained or not SKLEARN_AVAILABLE:
            return
            
        try:
            os.makedirs(os.path.dirname(self.model_path), exist_ok=True)
            with open(self.model_path, 'wb') as f:
                pickle.dump({
                    'model': self.model,
                    'scaler': self.scaler
                }, f)
            logger.info("ML Model saved successfully")
        except Exception as e:
            logger.error(f"Error saving ML model: {e}")

    def prepare_training_data(self, historical_trades: List[Dict]) -> Tuple[np.ndarray, np.ndarray]:
        """
        Geçmiş işlemleri eğitim verisine dönüştür
        """
        if not SKLEARN_AVAILABLE:
            return np.array([]), np.array([])
            
        X = []
        y = []
        
        for trade in historical_trades:
            # Gerekli feature'ların varlığını kontrol et
            if 'features' not in trade or 'profit_pct' not in trade:
                continue
                
            features = self._extract_features(trade['features'])
            if features is None:
                continue
                
            X.append(features)
            # Hedef: %2'den fazla kar ettiyse başarılı (1), değilse başarısız (0)
            y.append(1 if trade['profit_pct'] > 2.0 else 0)
            
        return np.array(X), np.array(y)
        
    def _extract_features(self, feature_dict: Dict) -> Optional[List[float]]:
        """Dictionary'den feature vektörü oluştur"""
        try:
            return [
                float(feature_dict.get('rsi', 50)),
                float(feature_dict.get('macd', 0)),
                float(feature_dict.get('adx', 0)),
                float(feature_dict.get('volume_ratio', 1.0)),
                float(feature_dict.get('trend_score', 50)),
                float(feature_dict.get('atr_percent', 2.0)),
                float(feature_dict.get('volatility', 0))
            ]
        except (ValueError, TypeError):
            return None

    def train(self, historical_trades: List[Dict]):
        """Modeli eğit"""
        if not SKLEARN_AVAILABLE:
            return
            
        X, y = self.prepare_training_data(historical_trades)
        
        if len(X) < 50:
            logger.warning("Not enough data to train ML model (min 50 samples)")
            return
            
        logger.info(f"Training ML model with {len(X)} samples...")
        X_scaled = self.scaler.fit_transform(X)
        self.model.fit(X_scaled, y)
        self.is_trained = True
        self.save_model()
    
    def train_from_dataframe(self, df: 'pd.DataFrame'):
        """
        DataFrame'den doğrudan eğit - VEKTÖRİZE ve HIZLI
        
        Args:
            df: Eğitim verisi DataFrame'i. Gerekli sütunlar:
                - rsi, macd, adx, volume_ratio, trend_score, atr_percent, volatility
                - profit_pct (hedef değişken)
        """
        if not SKLEARN_AVAILABLE:
            logger.warning("scikit-learn not available")
            return
        
        import pandas as pd
        
        required_cols = ['rsi', 'macd', 'adx', 'volume_ratio', 'trend_score', 'atr_percent', 'volatility', 'profit_pct']
        
        # Sütun isimlerini lowercase yap (case-sensitivity düzeltmesi)
        df.columns = [c.lower() for c in df.columns]
        
        missing = set(required_cols) - set(df.columns)
        if missing:
            logger.error(f"Eksik sütunlar: {missing}")
            return
        
        # Vektörize feature extraction
        feature_cols = ['rsi', 'macd', 'adx', 'volume_ratio', 'trend_score', 'atr_percent', 'volatility']
        X = df[feature_cols].values
        y = (df['profit_pct'] > 2.0).astype(int).values
        
        if len(X) < 50:
            logger.warning(f"Yetersiz veri: {len(X)} örnek (min 50 gerekli)")
            return
        
        logger.info(f"DataFrame'den eğitim: {len(X)} örnek...")
        X_scaled = self.scaler.fit_transform(X)
        self.model.fit(X_scaled, y)
        self.is_trained = True
        self.save_model()
        logger.info("Eğitim tamamlandı ve model kaydedildi.")
        
    def predict_signal_quality(self, signal_features: Dict) -> Dict:
        """
        Sinyal kalitesini tahmin et
        """
        if not self.is_trained or not SKLEARN_AVAILABLE:
            return {
                'prediction': 'UNKNOWN',
                'confidence': 0.0,
                'probability': 0.0
            }
            
        features = self._extract_features(signal_features)
        if features is None:
            return {'prediction': 'ERROR', 'confidence': 0.0, 'probability': 0.0}
            
        X = np.array([features])
        X_scaled = self.scaler.transform(X)
        
        # Tahmin
        prediction_class = self.model.predict(X_scaled)[0]
        probabilities = self.model.predict_proba(X_scaled)[0]
        
        # Class 1 (Başarılı) olasılığı
        success_prob = probabilities[1] if len(probabilities) > 1 else 0.0
        
        prediction = 'HIGH_QUALITY' if success_prob > 0.7 else \
                     'MEDIUM_QUALITY' if success_prob > 0.5 else \
                     'LOW_QUALITY'
                     
        return {
            'prediction': prediction,
            'confidence': success_prob,  # Güven skoru olarak başarı olasılığını kullanıyoruz
            'probability': success_prob * 100
        }
