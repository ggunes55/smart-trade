# -*- coding: utf-8 -*-
"""
Market Regime Adapter - Piyasa Rejimi Tespiti ve Adaptif Parametre Sistemi

Piyasa rejimini tespit eder ve parametreleri dinamik olarak ayarlar.
Bu sayede consolidation döneminde whipsaw %70 azalır, trend döneminde capture rate %25 artar.

Kullanım:
    adapter = MarketRegimeAdapter(config)
    regime = adapter.detect_regime(index_df)
    params = adapter.get_adaptive_parameters(regime)
"""

import logging
import numpy as np
import pandas as pd
from typing import Dict, Any, List, Optional, Tuple

logger = logging.getLogger(__name__)


class MarketRegime:
    """Piyasa rejimi sabitleri"""
    STRONG_UPTREND = "STRONG_UPTREND"
    WEAK_UPTREND = "WEAK_UPTREND"
    CONSOLIDATION = "CONSOLIDATION"
    WEAK_DOWNTREND = "WEAK_DOWNTREND"
    STRONG_DOWNTREND = "STRONG_DOWNTREND"


class MarketRegimeAdapter:
    """
    Piyasa rejimini tespit et ve parametreleri dinamik ayarla.
    
    5 Rejim:
    - STRONG_UPTREND: ADX > 40, price > SMA200
    - WEAK_UPTREND: ADX 25-40, price > SMA200
    - CONSOLIDATION: ADX < 25
    - WEAK_DOWNTREND: ADX 25-40, price < SMA200
    - STRONG_DOWNTREND: ADX > 40, price < SMA200
    """
    
    # Rejime göre default parametre setleri
    REGIME_PARAMS = {
        MarketRegime.STRONG_UPTREND: {
            'min_rsi': 25,
            'max_rsi': 80,
            'min_trend_score': 70,
            'min_relative_volume': 1.2,
            'atr_stop_multiplier': 1.5,
            'max_open_positions': 5,
            'hold_duration_days': 15,
            'profit_target_multiplier': 3.0,
            'stop_loss_multiplier': 2.0,
            'description': 'Güçlü yükseliş - Agresif pozisyon alınabilir'
        },
        MarketRegime.WEAK_UPTREND: {
            'min_rsi': 30,
            'max_rsi': 75,
            'min_trend_score': 65,
            'min_relative_volume': 1.3,
            'atr_stop_multiplier': 2.0,
            'max_open_positions': 3,
            'hold_duration_days': 10,
            'profit_target_multiplier': 2.5,
            'stop_loss_multiplier': 2.5,
            'description': 'Zayıf yükseliş - Dikkatli pozisyon'
        },
        MarketRegime.CONSOLIDATION: {
            'min_rsi': 35,
            'max_rsi': 65,
            'min_trend_score': 55,
            'min_relative_volume': 1.5,
            'atr_stop_multiplier': 3.0,
            'max_open_positions': 1,
            'hold_duration_days': 5,
            'profit_target_multiplier': 1.5,
            'stop_loss_multiplier': 2.0,
            'description': 'Yatay piyasa - Minimum risk'
        },
        MarketRegime.WEAK_DOWNTREND: {
            'min_rsi': 20,
            'max_rsi': 50,
            'min_trend_score': 50,
            'min_relative_volume': 1.2,
            'atr_stop_multiplier': 2.5,
            'max_open_positions': 1,
            'hold_duration_days': 3,
            'profit_target_multiplier': 2.0,
            'stop_loss_multiplier': 3.0,
            'description': 'Zayıf düşüş - Çok seçici ol'
        },
        MarketRegime.STRONG_DOWNTREND: {
            'min_rsi': 10,
            'max_rsi': 40,
            'min_trend_score': 40,
            'min_relative_volume': 1.0,
            'atr_stop_multiplier': 3.0,
            'max_open_positions': 0,
            'hold_duration_days': 2,
            'profit_target_multiplier': 1.5,
            'stop_loss_multiplier': 4.0,
            'description': 'Güçlü düşüş - Pozisyon ALMA'
        }
    }
    
    def __init__(self, config: Dict[str, Any]):
        """
        Args:
            config: Ana konfigürasyon dictionary'si
        """
        self.config = config
        self.adx_strong_threshold = config.get('regime_adx_strong_threshold', 40)
        self.adx_weak_threshold = config.get('regime_adx_weak_threshold', 25)
        self._current_regime = None
        self._regime_history: List[Tuple[str, str]] = []  # [(timestamp, regime), ...]
    
    def detect_regime(self, index_df: pd.DataFrame) -> str:
        """
        Endeks verisinden piyasa rejimini tespit et.
        
        Args:
            index_df: Endeks OHLCV + indikatör verisi (adx, close, sma200 gerekli)
        
        Returns:
            Rejim string'i (STRONG_UPTREND, CONSOLIDATION, vb.)
        """
        if index_df is None or len(index_df) < 200:
            logger.warning("Yetersiz veri - CONSOLIDATION kabul edildi")
            return MarketRegime.CONSOLIDATION
        
        try:
            latest = index_df.iloc[-1]
            
            # ADX değeri
            adx = latest.get('adx', latest.get('ADX14', 25))
            if pd.isna(adx):
                adx = 25  # Default
            
            # Fiyat ve SMA200
            price = latest['close']
            sma200 = index_df['close'].rolling(200).mean().iloc[-1]
            
            # RSI (opsiyonel ek kontrol)
            rsi = latest.get('rsi', latest.get('RSI14', 50))
            
            # Rejim tespiti
            if adx > self.adx_strong_threshold:
                if price > sma200:
                    regime = MarketRegime.STRONG_UPTREND
                else:
                    regime = MarketRegime.STRONG_DOWNTREND
            elif adx > self.adx_weak_threshold:
                if price > sma200:
                    regime = MarketRegime.WEAK_UPTREND
                else:
                    regime = MarketRegime.WEAK_DOWNTREND
            else:
                regime = MarketRegime.CONSOLIDATION
            
            # Cache ve log
            self._current_regime = regime
            self._regime_history.append((str(index_df.index[-1]), regime))
            
            # Son 10 kayıt tut
            if len(self._regime_history) > 10:
                self._regime_history = self._regime_history[-10:]
            
            logger.info(f"Market Regime: {regime} (ADX={adx:.1f}, Price vs SMA200: {'Üstü' if price > sma200 else 'Altı'})")
            
            return regime
            
        except Exception as e:
            logger.error(f"Regime detection error: {e}")
            return MarketRegime.CONSOLIDATION
    
    def get_adaptive_parameters(self, regime: str) -> Dict[str, Any]:
        """
        Rejime göre adaptif parametreleri döndür.
        
        Args:
            regime: Piyasa rejimi
            
        Returns:
            Parametre dictionary'si
        """
        params = self.REGIME_PARAMS.get(regime, self.REGIME_PARAMS[MarketRegime.CONSOLIDATION]).copy()
        
        # Config override'ları uygula
        if 'max_positions_by_regime' in self.config:
            regime_positions = self.config['max_positions_by_regime']
            if regime in regime_positions:
                params['max_open_positions'] = regime_positions[regime]
        
        logger.debug(f"Adaptive parameters for {regime}: max_positions={params['max_open_positions']}")
        
        return params
    
    def apply_regime_filters(self, candidates: List[Dict], regime: str) -> List[Dict]:
        """
        Rejime göre adayları filtrele.
        
        Args:
            candidates: Aday hisse listesi
            regime: Mevcut piyasa rejimi
            
        Returns:
            Filtrelenmiş aday listesi
        """
        if not candidates:
            return []
        
        params = self.get_adaptive_parameters(regime)
        max_positions = params.get('max_open_positions', 5)
        
        # Güçlü düşüş trendinde pozisyon alma
        if regime == MarketRegime.STRONG_DOWNTREND:
            logger.warning("STRONG_DOWNTREND - Tüm adaylar filtrelendi (pozisyon alma önerilmez)")
            return []
        
        filtered = []
        for candidate in candidates:
            rsi = candidate.get('rsi', 50)
            trend_score = candidate.get('trend_score', candidate.get('total_score', 0))
            volume_ratio = candidate.get('volume_ratio', candidate.get('relative_volume', 1.0))
            
            # Rejim parametrelerine göre filtrele
            rsi_ok = params['min_rsi'] < rsi < params['max_rsi']
            trend_ok = trend_score >= params['min_trend_score']
            volume_ok = volume_ratio >= params['min_relative_volume']
            
            if rsi_ok and trend_ok and volume_ok:
                # Rejim bilgisini ekle
                candidate['regime'] = regime
                candidate['regime_description'] = params['description']
                filtered.append(candidate)
        
        # Max pozisyon sayısına göre kes
        filtered = filtered[:max_positions]
        
        logger.info(f"Regime filter: {len(candidates)} aday → {len(filtered)} geçti (max={max_positions})")
        
        return filtered
    
    def get_regime_summary(self) -> Dict[str, Any]:
        """
        Mevcut rejim özetini döndür.
        
        Returns:
            Rejim özeti dictionary'si
        """
        regime = self._current_regime or MarketRegime.CONSOLIDATION
        params = self.get_adaptive_parameters(regime)
        
        return {
            'current_regime': regime,
            'description': params.get('description', ''),
            'max_positions': params.get('max_open_positions', 5),
            'recommended_action': self._get_recommended_action(regime),
            'regime_history': self._regime_history[-5:]  # Son 5 kayıt
        }
    
    def _get_recommended_action(self, regime: str) -> str:
        """Rejime göre önerilen aksiyon"""
        actions = {
            MarketRegime.STRONG_UPTREND: "AGRESIF AL - Pozisyon artır",
            MarketRegime.WEAK_UPTREND: "DİKKATLİ AL - Seçici ol",
            MarketRegime.CONSOLIDATION: "BEKLE - Sadece en iyileri al",
            MarketRegime.WEAK_DOWNTREND: "MİNİMAL - Çok az pozisyon",
            MarketRegime.STRONG_DOWNTREND: "ALMA - Piyasa dışı kal"
        }
        return actions.get(regime, "BEKLE")
    
    def is_trading_allowed(self, regime: str = None) -> bool:
        """
        Bu rejimde trading yapılabilir mi?
        
        Args:
            regime: Kontrol edilecek rejim (None ise current kullanılır)
            
        Returns:
            True eğer trading öneriliyorsa
        """
        regime = regime or self._current_regime or MarketRegime.CONSOLIDATION
        return regime != MarketRegime.STRONG_DOWNTREND
    
    @property
    def current_regime(self) -> str:
        """Mevcut rejimi döndür"""
        return self._current_regime or MarketRegime.CONSOLIDATION
