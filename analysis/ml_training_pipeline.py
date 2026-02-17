# -*- coding: utf-8 -*-
"""
ML Training Pipeline - FAZA 2

Backtest verilerinden ML modeli eğitmek ve parametreleri optimize etmek için pipeline.

Tarih: 12 Şubat 2026
Versiyon: 1.0 (FAZA 2)
"""

import logging
import numpy as np
import pandas as pd
from typing import Dict, Optional, Tuple, List
from dataclasses import dataclass
from pathlib import Path

try:
    import xgboost as xgb
    from sklearn.model_selection import train_test_split, cross_val_score
    from sklearn.preprocessing import StandardScaler
    from sklearn.metrics import accuracy_score, precision_score, recall_score, f1_score, roc_auc_score
    import pickle
except ImportError as e:
    logging.warning(f"ML Dependencies not fully installed: {e}")

logger = logging.getLogger(__name__)


@dataclass
class MLTrainingConfig:
    """ML eğitim konfigürasyonu"""
    test_size: float = 0.2
    random_state: int = 42
    xgb_max_depth: int = 6
    xgb_learning_rate: float = 0.1
    xgb_n_estimators: int = 200
    min_samples_per_label: int = 30  # En az 30 işlem/label
    cv_folds: int = 5


class MLTrainingPipeline:
    """
    Backtest sonuçlarından ML modeli eğiten pipeline
    
    Workflow:
    1. Trade verisi (backtest sonuçları)
    2. Feature extraction (teknik göstergeler)
    3. Label oluşturma (başarılı/başarısız)
    4. Train/test split
    5. Model eğitimi
    6. Validation ve metrikleri
    """
    
    def __init__(self, trades_df: pd.DataFrame, cfg: Optional[MLTrainingConfig] = None):
        """
        Args:
            trades_df: Backtest trade sonuçları
                Şu sütunları içermesi gerekir:
                - symbol: str
                - entry_date: datetime
                - entry_price: float
                - exit_date: datetime
                - exit_price: float
                - profit_pct: float
                - win/loss: bool
            cfg: Training configuration
        """
        self.trades = trades_df.copy()
        self.cfg = cfg or MLTrainingConfig()
        self.model = None
        self.scaler = None
        self.features_df = None
        self.labels = None
        self.feature_importance = None
        
        logger.info(f"✅ MLTrainingPipeline initialized with {len(self.trades)} trades")
    
    def validate_data(self) -> bool:
        """Backtest verisi doğrulaması"""
        required_columns = ['symbol', 'entry_price', 'exit_price', 'profit_pct']
        
        missing = set(required_columns) - set(self.trades.columns)
        if missing:
            logger.error(f"❌ Missing columns: {missing}")
            return False
        
        # Min işlem sayısını kontrol et
        if len(self.trades) < self.cfg.min_samples_per_label * 2:
            logger.warning(f"⚠️  Only {len(self.trades)} trades. Minimum {self.cfg.min_samples_per_label * 2} recommended")
            return False
        
        logger.info(f"✅ Data validation passed: {len(self.trades)} trades, {len(self.trades['symbol'].unique())} symbols")
        return True
    
    def extract_features(self) -> bool:
        """
        Backtest trade'lerinden features extract et
        
        Features:
        - price_momentum: (exit_price - entry_price) / entry_price
        - profit_pct: Brut kar %
        - volatility: İşlem süresi içindeki volatilite
        - trade_duration: İşlem süresi (gün)
        - win_sequence: Önceki işlemler başarılı mıydı?
        """
        try:
            features_list = []
            
            for idx, row in self.trades.iterrows():
                entry_price = float(row['entry_price'])
                exit_price = float(row['exit_price'])
                profit_pct = float(row.get('profit_pct', 0))
                
                # Temel features
                price_momentum = (exit_price - entry_price) / entry_price if entry_price > 0 else 0
                
                # İşlem süresi (gün)
                try:
                    trade_duration = (pd.to_datetime(row.get('exit_date', row.get('entry_date'))) - 
                                    pd.to_datetime(row.get('entry_date'))).days
                except:
                    trade_duration = 1
                
                # Win/Loss
                win = 1 if profit_pct > 0 else 0
                
                feature_row = {
                    'price_momentum': price_momentum,
                    'profit_pct': profit_pct,
                    'trade_duration': max(1, trade_duration),
                    'win': win
                }
                
                features_list.append(feature_row)
            
            self.features_df = pd.DataFrame(features_list)
            self.labels = self.features_df['win'].values
            
            # Feature normalization için scaler hazırla
            self.scaler = StandardScaler()
            feature_cols = ['price_momentum', 'profit_pct', 'trade_duration']
            self.features_df[feature_cols] = self.scaler.fit_transform(
                self.features_df[feature_cols]
            )
            
            logger.info(f"✅ Features extracted: {self.features_df.shape}")
            logger.info(f"   - Win rate: {self.labels.mean():.1%}")
            logger.info(f"   - Samples: {len(self.labels)}")
            
            return True
        
        except Exception as e:
            logger.error(f"❌ Feature extraction failed: {e}")
            return False
    
    def prepare_data(self) -> Tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray]:
        """
        Train/test split ve veri hazırlama
        
        Returns:
            X_train, X_test, y_train, y_test
        """
        if self.features_df is None or self.labels is None:
            if not self.extract_features():
                return None, None, None, None
        
        X = self.features_df[['price_momentum', 'profit_pct', 'trade_duration']].values
        y = self.labels
        
        # Stratified split (sınıf dengesi korunuyor)
        X_train, X_test, y_train, y_test = train_test_split(
            X, y,
            test_size=self.cfg.test_size,
            random_state=self.cfg.random_state,
            stratify=y
        )
        
        logger.info(f"✅ Data split: Train={len(X_train)}, Test={len(X_test)}")
        logger.info(f"   - Train win rate: {y_train.mean():.1%}")
        logger.info(f"   - Test win rate: {y_test.mean():.1%}")
        
        return X_train, X_test, y_train, y_test
    
    def train_model(self) -> bool:
        """XGBoost modeli eğit"""
        try:
            X_train, X_test, y_train, y_test = self.prepare_data()
            
            if X_train is None:
                return False
            
            # XGBoost modeli oluştur
            self.model = xgb.XGBClassifier(
                max_depth=self.cfg.xgb_max_depth,
                learning_rate=self.cfg.xgb_learning_rate,
                n_estimators=self.cfg.xgb_n_estimators,
                random_state=self.cfg.random_state,
                use_label_encoder=False,
                eval_metric='logloss'
            )
            
            # Eğit
            self.model.fit(
                X_train, y_train,
                eval_set=[(X_test, y_test)],
                verbose=False
            )
            
            # Feature importance
            self.feature_importance = dict(zip(
                ['price_momentum', 'profit_pct', 'trade_duration'],
                self.model.feature_importances_
            ))
            
            logger.info(f"✅ Model trained successfully")
            logger.info(f"   - Feature importance:")
            for feat, imp in sorted(self.feature_importance.items(), key=lambda x: x[1], reverse=True):
                logger.info(f"     - {feat}: {imp:.3f}")
            
            return True
        
        except Exception as e:
            logger.error(f"❌ Model training failed: {e}")
            return False
    
    def evaluate(self) -> Dict[str, float]:
        """Model değerlendirmesi"""
        try:
            if self.model is None:
                if not self.train_model():
                    return {}
            
            X_train, X_test, y_train, y_test = self.prepare_data()
            
            if X_test is None:
                return {}
            
            # Predictions
            y_pred = self.model.predict(X_test)
            y_pred_proba = self.model.predict_proba(X_test)[:, 1]
            
            # Metrics
            metrics = {
                'accuracy': accuracy_score(y_test, y_pred),
                'precision': precision_score(y_test, y_pred, zero_division=0),
                'recall': recall_score(y_test, y_pred, zero_division=0),
                'f1': f1_score(y_test, y_pred, zero_division=0),
                'auc_roc': roc_auc_score(y_test, y_pred_proba)
            }
            
            logger.info(f"✅ Model Evaluation:")
            logger.info(f"   - Accuracy:  {metrics['accuracy']:.1%}")
            logger.info(f"   - Precision: {metrics['precision']:.1%}")
            logger.info(f"   - Recall:    {metrics['recall']:.1%}")
            logger.info(f"   - F1-Score:  {metrics['f1']:.3f}")
            logger.info(f"   - AUC-ROC:   {metrics['auc_roc']:.3f}")
            
            # Cross-validation
            cv_scores = cross_val_score(self.model, X_test, y_test, cv=self.cfg.cv_folds, scoring='f1')
            metrics['cv_mean'] = cv_scores.mean()
            metrics['cv_std'] = cv_scores.std()
            logger.info(f"   - CV F1 (5-fold): {metrics['cv_mean']:.3f} ± {metrics['cv_std']:.3f}")
            
            return metrics
        
        except Exception as e:
            logger.error(f"❌ Evaluation failed: {e}")
            return {}
    
    def save_model(self, filepath: str) -> bool:
        """Modeli dosyaya kaydet"""
        try:
            if self.model is None:
                logger.error("❌ No model to save")
                return False
            
            Path(filepath).parent.mkdir(parents=True, exist_ok=True)
            
            model_data = {
                'model': self.model,
                'scaler': self.scaler,
                'feature_importance': self.feature_importance,
                'config': self.cfg
            }
            
            with open(filepath, 'wb') as f:
                pickle.dump(model_data, f)
            
            logger.info(f"✅ Model saved to {filepath}")
            return True
        
        except Exception as e:
            logger.error(f"❌ Save failed: {e}")
            return False
    
    @staticmethod
    def load_model(filepath: str) -> Optional['MLTrainingPipeline']:
        """Kaydedilmiş modeli yükle"""
        try:
            with open(filepath, 'rb') as f:
                model_data = pickle.load(f)
            
            pipeline = MLTrainingPipeline(pd.DataFrame())
            pipeline.model = model_data['model']
            pipeline.scaler = model_data['scaler']
            pipeline.feature_importance = model_data['feature_importance']
            pipeline.cfg = model_data['config']
            
            logger.info(f"✅ Model loaded from {filepath}")
            return pipeline
        
        except Exception as e:
            logger.error(f"❌ Load failed: {e}")
            return None


# ============================================================================
# ÖRNEK KULLANIM
# ============================================================================

if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s'
    )
    
    # Örnek: Backtest verisi (gerçekte backtester.py'dan gelir)
    sample_trades = pd.DataFrame({
        'symbol': ['SUWEN', 'TRKCM', 'SASA'] * 20,
        'entry_date': pd.date_range('2025-01-01', periods=60),
        'entry_price': np.random.uniform(10, 100, 60),
        'exit_date': pd.date_range('2025-01-02', periods=60),
        'exit_price': np.random.uniform(10, 100, 60),
        'profit_pct': np.random.uniform(-5, 15, 60),
    })
    
    # Pipeline çalıştır
    pipeline = MLTrainingPipeline(sample_trades)
    
    if pipeline.validate_data():
        if pipeline.train_model():
            metrics = pipeline.evaluate()
            pipeline.save_model('models/signal_predictor_v1.pkl')
            
            print("\n" + "="*60)
            print("FAZA 2: ML Training Pipeline Başarılı!")
            print("="*60)
        else:
            print("❌ Training failed")
    else:
        print("❌ Data validation failed")

