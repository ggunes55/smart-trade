# -*- coding: utf-8 -*-
"""
Entry Timing Optimizer - Optimal Giriş Noktası Belirleme

Sinyal tipine göre en iyi giriş noktasını ve zamanını belirler.
Erken giriş riskini azaltır, geç girişten kaynaklanan fırsat kaybını önler.

Kullanım:
    optimizer = EntryTimingOptimizer(config)
    entry = optimizer.optimal_entry_point(df, signal_type='BREAKOUT')
    is_valid, reasons = optimizer.entry_validation_checklist(df, symbol)
"""

import logging
import numpy as np
import pandas as pd
from typing import Dict, Any, Optional, Tuple, List
from enum import Enum

logger = logging.getLogger(__name__)


class SignalType(Enum):
    """Sinyal tipleri"""
    BREAKOUT = "BREAKOUT"      # Direnç kırılımı
    PULLBACK = "PULLBACK"      # Düzeltme sonrası alım
    REVERSAL = "REVERSAL"      # Trend dönüşü
    MOMENTUM = "MOMENTUM"      # Momentum devamı
    SQUEEZE = "SQUEEZE"        # Volatilite sıkışma çıkışı


class EntryTimingOptimizer:
    """
    Optimal giriş noktasını belirle.
    
    Signal tipine göre:
    - BREAKOUT: Resistance + %0.5 geçtikten sonra + volume confirmation
    - PULLBACK: Support'a yakın + momentum korunmuş
    - REVERSAL: Candlestick pattern + volume explosion
    - MOMENTUM: Trend devam + RSI moderat
    - SQUEEZE: BB squeeze çözülüşü + directional breakout
    """
    
    def __init__(self, config: Dict[str, Any]):
        """
        Args:
            config: Ana konfigürasyon dictionary'si
        """
        self.config = config
        self.breakout_confirmation_pct = config.get('breakout_confirmation_pct', 0.5)
        self.volume_surge_threshold = config.get('min_volume_surge', 1.5)
        self.support_distance_min = config.get('support_distance_min', 1.0)
        self.support_distance_max = config.get('support_distance_max', 3.0)
    
    def detect_signal_type(self, df: pd.DataFrame) -> SignalType:
        """
        Veri paterninden sinyal tipini otomatik tespit et.
        
        Args:
            df: OHLCV + indikatör verisi
            
        Returns:
            SignalType enum değeri
        """
        if df is None or len(df) < 20:
            return SignalType.MOMENTUM
        
        latest = df.iloc[-1]
        
        try:
            # Squeeze kontrolü
            if 'squeeze' in df.columns or 'bb_squeeze' in df.columns:
                squeeze_val = latest.get('squeeze', latest.get('bb_squeeze', False))
                if squeeze_val:
                    return SignalType.SQUEEZE
            
            # Breakout kontrolü: Son fiyat 20 günlük high'ın üzerinde mi?
            high_20 = df['high'].rolling(20).max().iloc[-2]  # Önceki bar'ın max'ı
            if latest['close'] > high_20:
                return SignalType.BREAKOUT
            
            # Pullback kontrolü: RSI düşük ama trend yukarı
            rsi = latest.get('rsi', latest.get('RSI14', 50))
            ema20 = df['close'].rolling(20).mean().iloc[-1]
            ema50 = df['close'].rolling(50).mean().iloc[-1]
            
            if rsi < 40 and ema20 > ema50:
                return SignalType.PULLBACK
            
            # Reversal kontrolü: RSI aşırı düşükten döndü
            if len(df) >= 3:
                prev_rsi = df.iloc[-3].get('rsi', df.iloc[-3].get('RSI14', 50))
                if prev_rsi < 30 and rsi > 35:
                    return SignalType.REVERSAL
            
            # Default: Momentum
            return SignalType.MOMENTUM
            
        except Exception as e:
            logger.debug(f"Signal type detection error: {e}")
            return SignalType.MOMENTUM
    
    def optimal_entry_point(self, df: pd.DataFrame, signal_type: str = None) -> Optional[Dict[str, Any]]:
        """
        Sinyal tipine göre optimal entry noktası.
        
        Args:
            df: OHLCV + indikatör verisi
            signal_type: Sinyal tipi (None ise otomatik tespit)
            
        Returns:
            Entry bilgisi dictionary veya None
        """
        if df is None or len(df) < 20:
            return None
        
        # Sinyal tipini belirle
        if signal_type is None:
            sig_type = self.detect_signal_type(df)
        else:
            try:
                sig_type = SignalType(signal_type.upper())
            except ValueError:
                sig_type = SignalType.MOMENTUM
        
        latest = df.iloc[-1]
        current_price = latest['close']
        
        try:
            if sig_type == SignalType.BREAKOUT:
                return self._breakout_entry(df, latest)
            
            elif sig_type == SignalType.PULLBACK:
                return self._pullback_entry(df, latest)
            
            elif sig_type == SignalType.REVERSAL:
                return self._reversal_entry(df, latest)
            
            elif sig_type == SignalType.SQUEEZE:
                return self._squeeze_entry(df, latest)
            
            else:  # MOMENTUM
                return self._momentum_entry(df, latest)
                
        except Exception as e:
            logger.error(f"Entry point calculation error: {e}")
            return {
                'entry_price': current_price,
                'signal_type': sig_type.value,
                'confidence': 0.5,
                'reason': f'Default entry (error: {e})'
            }
    
    def _breakout_entry(self, df: pd.DataFrame, latest: pd.Series) -> Dict[str, Any]:
        """Breakout giriş stratejisi"""
        resistance = df['high'].rolling(20).max().iloc[-1]
        entry_price = resistance * (1 + self.breakout_confirmation_pct / 100)
        
        # Volume confirmation
        volume_sma = df['volume'].rolling(20).mean().iloc[-1]
        volume_ok = latest['volume'] > volume_sma * self.volume_surge_threshold
        
        confidence = 0.95 if volume_ok else 0.70
        
        return {
            'entry_price': round(entry_price, 4),
            'signal_type': SignalType.BREAKOUT.value,
            'confidence': confidence,
            'resistance_level': round(resistance, 4),
            'volume_confirmed': volume_ok,
            'reason': f"Resistance ({resistance:.2f}) + {self.breakout_confirmation_pct}% confirmation"
        }
    
    def _pullback_entry(self, df: pd.DataFrame, latest: pd.Series) -> Dict[str, Any]:
        """Pullback giriş stratejisi"""
        support = df['low'].rolling(20).min().iloc[-1]
        entry_price = support * 1.01  # Support'tan %1 yukarı
        
        # RSI kontrolü
        rsi = latest.get('rsi', latest.get('RSI14', 50))
        rsi_ok = rsi < 50
        
        confidence = 0.90 if rsi_ok else 0.65
        
        return {
            'entry_price': round(entry_price, 4),
            'signal_type': SignalType.PULLBACK.value,
            'confidence': confidence,
            'support_level': round(support, 4),
            'rsi': rsi,
            'reason': f"Support yakını ({support:.2f}) + RSI={rsi:.1f}"
        }
    
    def _reversal_entry(self, df: pd.DataFrame, latest: pd.Series) -> Dict[str, Any]:
        """Reversal giriş stratejisi"""
        entry_price = latest['close']
        
        # Volume explosion kontrolü
        volume_sma = df['volume'].rolling(10).mean().iloc[-1]
        volume_explosion = latest['volume'] > volume_sma * 2
        
        confidence = 0.85 if volume_explosion else 0.60
        
        return {
            'entry_price': round(entry_price, 4),
            'signal_type': SignalType.REVERSAL.value,
            'confidence': confidence,
            'volume_explosion': volume_explosion,
            'reason': "Reversal pattern + volume"
        }
    
    def _squeeze_entry(self, df: pd.DataFrame, latest: pd.Series) -> Dict[str, Any]:
        """Squeeze breakout giriş stratejisi"""
        entry_price = latest['close']
        
        # Squeeze direction (MACD veya momentum ile)
        macd = latest.get('macd', latest.get('MACD', 0))
        bullish = macd > 0
        
        confidence = 0.88 if bullish else 0.50
        
        return {
            'entry_price': round(entry_price, 4),
            'signal_type': SignalType.SQUEEZE.value,
            'confidence': confidence,
            'direction': 'BULLISH' if bullish else 'BEARISH',
            'reason': f"Squeeze release - {'Bullish' if bullish else 'Bearish'} direction"
        }
    
    def _momentum_entry(self, df: pd.DataFrame, latest: pd.Series) -> Dict[str, Any]:
        """Momentum devam giriş stratejisi"""
        entry_price = latest['close']
        
        # Trend alignment kontrolü
        ema20 = df['close'].rolling(20).mean().iloc[-1]
        ema50 = df['close'].rolling(50).mean().iloc[-1]
        trend_aligned = ema20 > ema50 and latest['close'] > ema20
        
        confidence = 0.80 if trend_aligned else 0.55
        
        return {
            'entry_price': round(entry_price, 4),
            'signal_type': SignalType.MOMENTUM.value,
            'confidence': confidence,
            'trend_aligned': trend_aligned,
            'reason': "Momentum continuation"
        }
    
    def entry_validation_checklist(self, df: pd.DataFrame, symbol: str = "") -> Tuple[bool, Dict[str, bool], List[str]]:
        """
        Giriş öncesi doğrulama kontrol listesi.
        
        Args:
            df: OHLCV + indikatör verisi
            symbol: Sembol (loglama için)
            
        Returns:
            (all_passed: bool, checklist: dict, failed_items: list)
        """
        if df is None or len(df) < 20:
            return False, {}, ["Yetersiz veri"]
        
        latest = df.iloc[-1]
        failed_items = []
        
        checklist = {
            'volume_above_average': False,
            'rsi_not_extreme': False,
            'trend_aligned': False,
            'support_nearby': False,
            'momentum_positive': False,
            'volatility_acceptable': False,
        }
        
        try:
            # 1. Volume kontrolü
            volume_sma = df['volume'].rolling(20).mean().iloc[-1]
            checklist['volume_above_average'] = latest['volume'] > volume_sma
            if not checklist['volume_above_average']:
                failed_items.append("Hacim ortalama altında")
            
            # 2. RSI kontrolü
            rsi = latest.get('rsi', latest.get('RSI14', 50))
            checklist['rsi_not_extreme'] = 25 < rsi < 75
            if not checklist['rsi_not_extreme']:
                failed_items.append(f"RSI extreme ({rsi:.1f})")
            
            # 3. Trend alignment
            ema20 = df['close'].rolling(20).mean().iloc[-1]
            ema50 = df['close'].rolling(50).mean().iloc[-1]
            checklist['trend_aligned'] = latest['close'] > ema20 and ema20 > ema50
            if not checklist['trend_aligned']:
                failed_items.append("Trend uyumsuz")
            
            # 4. Support yakınlığı
            support = df['low'].rolling(20).min().iloc[-1]
            if support > 0:
                distance_pct = ((latest['close'] - support) / support) * 100
                checklist['support_nearby'] = self.support_distance_min < distance_pct < self.support_distance_max * 2
                if not checklist['support_nearby']:
                    failed_items.append(f"Support mesafesi: {distance_pct:.1f}%")
            
            # 5. Momentum kontrolü
            macd = latest.get('macd', latest.get('MACD', 0))
            macd_signal = latest.get('macd_signal', latest.get('MACD_Signal', 0))
            checklist['momentum_positive'] = macd > macd_signal
            if not checklist['momentum_positive']:
                failed_items.append("MACD negatif crossover")
            
            # 6. Volatilite kontrolü
            atr = latest.get('ATR14', latest.get('atr', 0))
            if atr > 0:
                atr_pct = (atr / latest['close']) * 100
                checklist['volatility_acceptable'] = 0.5 < atr_pct < 5.0
                if not checklist['volatility_acceptable']:
                    failed_items.append(f"Volatilite aşırı: ATR%={atr_pct:.1f}")
            else:
                checklist['volatility_acceptable'] = True
            
        except Exception as e:
            logger.error(f"Validation checklist error for {symbol}: {e}")
            failed_items.append(f"Hata: {e}")
        
        # Sonuç
        all_passed = all(checklist.values())
        passed_count = sum(checklist.values())
        
        if all_passed:
            logger.info(f"{symbol}: ✅ ALL GREEN - OPTIMAL ENTRY (6/6)")
        else:
            logger.info(f"{symbol}: ⚠️ WAIT - {passed_count}/6 passed. Missing: {failed_items}")
        
        return all_passed, checklist, failed_items
    
    def get_entry_recommendation(self, df: pd.DataFrame, symbol: str = "") -> Dict[str, Any]:
        """
        Kapsamlı giriş önerisi.
        
        Returns:
            Entry recommendation dictionary
        """
        # Optimal entry noktası
        entry_info = self.optimal_entry_point(df)
        
        # Validation checklist
        is_valid, checklist, failed = self.entry_validation_checklist(df, symbol)
        
        # Genel öneri
        if is_valid and entry_info and entry_info.get('confidence', 0) > 0.75:
            recommendation = "STRONG BUY"
            action = "Hemen gir"
        elif is_valid or (entry_info and entry_info.get('confidence', 0) > 0.60):
            recommendation = "BUY"
            action = "Fırsatı değerlendir"
        else:
            recommendation = "WAIT"
            action = "Daha iyi giriş noktası bekle"
        
        return {
            'symbol': symbol,
            'recommendation': recommendation,
            'action': action,
            'entry_info': entry_info,
            'validation_passed': is_valid,
            'checklist': checklist,
            'failed_checks': failed,
            'overall_confidence': entry_info.get('confidence', 0) if entry_info else 0
        }
