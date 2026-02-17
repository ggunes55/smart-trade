# -*- coding: utf-8 -*-
"""
Integration Engine - Tüm Advanced Analiz Modüllerini Bir Yerde Kullan
Bu dosya, FAZA 1 iyileştirmesinin çekirdeğidir.

Tarih: 11 Şubat 2026
Versiyon: 1.0
"""
import logging
import os
import json
import numpy as np
import pandas as pd
from typing import Dict, Optional, List, Tuple
from dataclasses import dataclass

logger = logging.getLogger(__name__)


@dataclass
class ConfirmedSignal:
    """
    Tam onaylanmış bir trading sinyali
    """
    is_valid: bool
    symbol: str
    signal_type: str  # "BUY", "SELL"
    base_score: float  # 0-100
    confirmation_score: float  # 0-100
    ml_confidence: float  # 0-100
    entry_timing_score: float  # 0-100
    
    final_score: float  # Weighted average
    recommendation: str  # "STRONG BUY", "BUY", "HOLD", "SELL", "STRONG SELL"
    confidence_level: str  # "HIGH", "MEDIUM", "LOW"
    
    # Detay bilgiler
    confirmation_reasons: List[str]
    rejection_reasons: List[str]
    
    # Entry önerisi
    optimal_entry_price: Optional[float] = None
    stop_loss: Optional[float] = None
    target_prices: Optional[List[float]] = None


class AnalysisIntegrationEngine:
    """
    Advanced analiz pipeline orchestrator
    
    Mevcut modülleri şu sırada kullan:
    1. Signal Confirmation - Temel sinyali doğrula
    2. ML Classifier - Sinyal olasılığı tahmin et
    3. Entry Timing - Giriş zamanını optimize et
    4. Risk Management - Stop/target belirle
    """
    
    def __init__(self, cfg: Dict, 
                 signal_confirmer=None,
                 ml_classifier=None,
                 entry_optimizer=None):
        """
        Args:
            cfg: Configuration dictionary
            signal_confirmer: SignalConfirmationFilter instance
            ml_classifier: MLSignalClassifier instance
            entry_optimizer: EntryTimingOptimizer instance
        """
        self.cfg = cfg
        
        # Lazy import to avoid circular dependencies
        self.signal_confirmer = signal_confirmer
        if self.signal_confirmer is None and cfg.get('use_signal_confirmation', True):
            logger.debug("SignalConfirmationFilter will be initialized with actual data during analysis")
        
        try:
            from analysis.ml_signal_classifier import MLSignalClassifier
            self.ml_classifier = ml_classifier or MLSignalClassifier()
        except Exception as e:
            logger.warning(f"MLSignalClassifier init failed: {e}")
            self.ml_classifier = None
        
        try:
            from analysis.entry_timing import EntryTimingOptimizer
            self.entry_optimizer = entry_optimizer or EntryTimingOptimizer(cfg)
        except Exception as e:
            logger.warning(f"EntryTimingOptimizer init failed: {e}")
            self.entry_optimizer = None
        
        # Weighting configuration (varsayılan)
        self.weights = cfg.get(
            'integration_weights',
            {
                'base_signal': 0.25,
                'confirmation': 0.25,
                'ml_confidence': 0.30,
                'entry_timing': 0.20,
            },
        )

        # Opsiyonel: FAZA 2 ile optimize edilmiş ağırlıkları otomatik yükle
        optimized_path = cfg.get('integration_weights_file', 'analysis/optimized_weights_faza2.json')
        try:
            if os.path.exists(optimized_path):
                with open(optimized_path, 'r', encoding='utf-8') as f:
                    data = json.load(f)

                # FAZA 2 lightweight dosya formatı: {'best_weights': {...}, ...}
                best_weights = data.get('best_weights', data)
                required_keys = {'base_signal', 'confirmation', 'ml_confidence', 'entry_timing'}

                if required_keys.issubset(best_weights.keys()):
                    self.weights = {
                        'base_signal': float(best_weights['base_signal']),
                        'confirmation': float(best_weights['confirmation']),
                        'ml_confidence': float(best_weights['ml_confidence']),
                        'entry_timing': float(best_weights['entry_timing']),
                    }
                    logger.info(f"✅ Using optimized integration weights from {optimized_path}")
                else:
                    logger.warning(f"Optimized weights file missing required keys, using config defaults: {optimized_path}")
        except Exception as e:
            logger.warning(f"Could not load optimized integration weights: {e}")
        
        logger.info("✅ AnalysisIntegrationEngine initialized")
    
    def full_analysis_pipeline(self,
                               symbol: str,
                               data: pd.DataFrame,
                               base_signal: Dict,
                               market_context: Optional[Dict] = None) -> Optional[ConfirmedSignal]:
        """
        FAZA 1 - ENTEGRASYON PIPELINE
        
        Tüm advanced modülleri sırasıyla kullan:
        1. Signal confirmation ✓
        2. ML classification ✓
        3. Entry timing optimization ✓
        4. Final scoring ✓
        
        Args:
            symbol: Stock symbol
            data: OHLCV DataFrame
            base_signal: Temel sinyal (signal_type, score, vb.)
            market_context: Piyasa rejimi, volatilite, vb.
        
        Returns:
            ConfirmedSignal or None
        """
        
        if not base_signal:
            return None
        
        logger.debug(f"🔗 Starting integration pipeline for {symbol}")
        
        confirmed_signal = ConfirmedSignal(
            is_valid=False,
            symbol=symbol,
            signal_type=base_signal.get('signal_type', 'UNKNOWN'),
            base_score=base_signal.get('score', 0),
            confirmation_score=0,
            ml_confidence=0,
            entry_timing_score=0,
            final_score=0,
            recommendation='HOLD',
            confidence_level='LOW',
            confirmation_reasons=[],
            rejection_reasons=[]
        )
        
        # STEP 1: Signal Confirmation
        # =========================================================================
        if self.signal_confirmer and self.cfg.get('use_signal_confirmation', True):
            logger.debug(f"  [1/3] Signal confirmation for {symbol}...")
            
            try:
                # Initialize SignalConfirmationFilter with actual data
                from analysis.signal_confirmation import SignalConfirmationFilter
                confirmer = SignalConfirmationFilter(data, self.cfg)
                
                # Multi-source confirmation returns (is_valid, confirmation_count, details)
                is_valid, confirmation_count, details = confirmer.multi_source_confirmation()
                
                if is_valid and confirmation_count >= 3:
                    confirmed_signal.confirmation_score = min(100, 60 + confirmation_count * 10)
                    confirmed_signal.confirmation_reasons = details.get('reasons', [])
                    logger.debug(f"  ✅ Confirmation passed: {confirmed_signal.confirmation_score:.1f}")
                else:
                    confirmed_signal.rejection_reasons.append(
                        f"Confirmation filter rejected: Only {confirmation_count}/6 sources confirmed"
                    )
                    logger.debug(f"  ❌ Confirmation failed: {confirmation_count} confirmations")
            
            except Exception as e:
                logger.warning(f"Signal confirmation error: {e}")
                confirmed_signal.rejection_reasons.append(f"Confirmation error: {str(e)}")
        else:
            confirmed_signal.confirmation_score = base_signal.get('score', 0)
        
        # STEP 2: ML Classification
        # =========================================================================
        if self.ml_classifier and self.cfg.get('use_ml_classifier', True):
            logger.debug(f"  [2/3] ML classification for {symbol}...")
            
            try:
                # Feature extraction for ML-based confidence
                features = self._extract_ml_features(data, base_signal)
                
                if features is not None:
                    # Calculate feature-based confidence score (0-1 range)
                    # When ML model is untrained, use feature analysis
                    if not self.ml_classifier or not self.ml_classifier.is_trained:
                        # Fallback: calculate confidence from features directly
                        rsi = features.get('rsi', 50)
                        volume_ratio = features.get('volume_ratio', 1.0)
                        trend_score = features.get('trend_score', 50)
                        
                        # RSI moderation (30-70 is good)
                        rsi_quality = 1.0 if 30 < rsi < 70 else 0.5
                        # Volume confirmation (should be > 1.0x average)
                        volume_quality = min(1.0, volume_ratio / 2.0) if volume_ratio > 0 else 0.3
                        # Trend alignment
                        trend_quality = (trend_score / 100.0) if trend_score >= 50 else (100 - trend_score) / 100.0
                        
                        ml_score = (rsi_quality * 0.4 + volume_quality * 0.4 + trend_quality * 0.2)
                    else:
                        ml_result = self.ml_classifier.predict_signal_quality(features)
                        ml_score = ml_result.get('confidence', 0.5) if isinstance(ml_result, dict) else 0.5
                    
                    confirmed_signal.ml_confidence = ml_score * 100  # Convert to 0-100 scale
                    
                    if ml_score > 0.65:
                        confirmed_signal.confirmation_reasons.append(
                            f"ML confidence high: {ml_score:.1%}"
                        )
                    elif ml_score < 0.40:
                        confirmed_signal.rejection_reasons.append(
                            f"ML confidence low: {ml_score:.1%}"
                        )
                    
                    logger.debug(f"  🤖 ML Score: {ml_score:.1%}")
            
            except Exception as e:
                logger.warning(f"ML classification error: {e}")
                # Fallback to base signal confidence
                confirmed_signal.ml_confidence = base_signal.get('score', 60)
        
        # STEP 3: Entry Timing Optimization
        # =========================================================================
        if self.entry_optimizer and self.cfg.get('use_entry_timing', True):
            logger.debug(f"  [3/3] Entry timing optimization for {symbol}...")
            
            try:
                entry_result = self.entry_optimizer.optimal_entry_point(
                    df=data,
                    signal_type=base_signal.get('signal_type')
                )
                
                if entry_result:
                    # Extract entry timing score from result
                    entry_confidence = entry_result.get('confidence', 0.5)
                    confirmed_signal.entry_timing_score = entry_confidence * 100
                    confirmed_signal.optimal_entry_price = entry_result.get('entry_price')
                    
                    if entry_confidence >= 0.85:
                        confirmed_signal.confirmation_reasons.append(
                            f"High confidence entry: {confirmed_signal.optimal_entry_price:.2f}"
                        )
                    
                    logger.debug(f"  ⏱️  Entry: {confirmed_signal.optimal_entry_price:.2f} (conf={entry_confidence:.1%})")
                else:
                    confirmed_signal.entry_timing_score = 50
                    logger.debug(f"  ⚠️  Entry timing unavailable")
            
            except Exception as e:
                logger.warning(f"Entry timing error: {e}")
                confirmed_signal.entry_timing_score = 50
        
        # STEP 4: Final Scoring & Recommendation
        # =========================================================================
        confirmed_signal.final_score = self._calculate_weighted_score(
            base_score=confirmed_signal.base_score,
            confirmation_score=confirmed_signal.confirmation_score,
            ml_confidence=confirmed_signal.ml_confidence,
            entry_timing_score=confirmed_signal.entry_timing_score
        )
        
        # Determine recommendation
        confirmed_signal.is_valid = confirmed_signal.final_score > self.cfg.get('min_signal_score', 60)
        confirmed_signal.recommendation = self._score_to_recommendation(confirmed_signal.final_score)
        confirmed_signal.confidence_level = self._score_to_confidence(confirmed_signal.final_score)
        
        logger.info(
            f"🎯 {symbol}: "
            f"Base={confirmed_signal.base_score:.0f} | "
            f"Conf={confirmed_signal.confirmation_score:.0f} | "
            f"ML={confirmed_signal.ml_confidence:.0f} | "
            f"Entry={confirmed_signal.entry_timing_score:.0f} | "
            f"Final={confirmed_signal.final_score:.0f} ➜ {confirmed_signal.recommendation}"
        )
        
        return confirmed_signal
    
    # =========================================================================
    # Helper Methods
    # =========================================================================
    
    def _extract_ml_features(self, data: pd.DataFrame, base_signal: Dict) -> Optional[Dict[str, float]]:
        """
        ML model için feature extraction - Dict format
        """
        try:
            if len(data) < 20:
                return None
            
            close = data['close'].values
            high = data['high'].values
            volume = data['volume'].values
            
            # Technical features as dictionary
            features = {
                'rsi': float(base_signal.get('rsi', 50)),
                'macd': float(base_signal.get('macd', 0)),
                'atr_percent': float(base_signal.get('atr_percent', 0)),
                'volatility': float((close[-1] / close[-20] - 1) * 100),
                'volume_ratio': float(volume[-1] / np.mean(volume[-20:])),
                'trend_score': float(base_signal.get('trend_score', 50))
            }
            
            return features
        except Exception as e:
            logger.warning(f"Feature extraction error: {e}")
            return None
    
    def _calculate_weighted_score(self,
                                  base_score: float,
                                  confirmation_score: float,
                                  ml_confidence: float,
                                  entry_timing_score: float) -> float:
        """
        Weighted average final score (all inputs should be 0-100 scale)
        """
        weighted_sum = (
            base_score * self.weights['base_signal'] +
            confirmation_score * self.weights['confirmation'] +
            ml_confidence * self.weights['ml_confidence'] +
            entry_timing_score * self.weights['entry_timing']
        )
        
        total_weight = sum(self.weights.values())
        return min(100, weighted_sum / total_weight)
    
    def _score_to_recommendation(self, score: float) -> str:
        """Convert score to recommendation string"""
        if score >= 85:
            return "STRONG BUY"
        elif score >= 70:
            return "BUY"
        elif score >= 55:
            return "HOLD"
        elif score >= 40:
            return "SELL"
        else:
            return "STRONG SELL"
    
    def _score_to_confidence(self, score: float) -> str:
        """Convert score to confidence level"""
        if score >= 75:
            return "HIGH"
        elif score >= 55:
            return "MEDIUM"
        else:
            return "LOW"


# ============================================================================
# KULLANIM ÖRNEĞİ - symbol_analyzer.py içinde nasıl kullanılacak
# ============================================================================

"""
from analysis.integration_engine import AnalysisIntegrationEngine

class SymbolAnalyzer:
    def __init__(self, cfg, ...):
        # ... existing code ...
        self.integration_engine = AnalysisIntegrationEngine(cfg)
    
    def analyze_symbol(self, symbol: str, ...):
        # ... mevcut temel analiz ...
        base_signal = {
            'signal_type': 'BUY',
            'score': 72,
            'rsi': 35,
            'macd': 0.5,
            'atr_percent': 1.2,
            # ... diğer parametreler ...
        }
        
        # YENİ: Full integration pipeline
        confirmed = self.integration_engine.full_analysis_pipeline(
            symbol=symbol,
            data=data,
            base_signal=base_signal,
            market_context=market_analysis
        )
        
        if confirmed and confirmed.is_valid:
            result['integrated_score'] = confirmed.final_score
            result['recommendation'] = confirmed.recommendation
            result['confidence'] = confirmed.confidence_level
            result['optimal_entry'] = confirmed.optimal_entry_price
            return result
        else:
            return None
"""
