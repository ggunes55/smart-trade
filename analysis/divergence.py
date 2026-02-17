# analysis/divergence.py
# -*- coding: utf-8 -*-
"""
RSI/Price Divergence Tespiti
Swing trade için güçlü dönüş sinyalleri
"""
import pandas as pd
import numpy as np
from typing import Dict, List, Tuple, Optional
from dataclasses import dataclass


@dataclass
class DivergenceSignal:
    """Divergence sinyal bilgisi"""
    type: str  # 'bullish' veya 'bearish'
    strength: str  # 'strong', 'moderate', 'weak'
    price_trend: float
    indicator_trend: float
    confidence: float
    bar_distance: int  # Kaç bar önceki swing point


def find_swing_points(series: pd.Series, window: int = 5) -> Tuple[List[int], List[int]]:
    """
    Swing high ve low noktalarını bul
    
    Args:
        series: Fiyat veya indikatör serisi
        window: Swing tespit penceresi
    
    Returns:
        (swing_high_indices, swing_low_indices)
    """
    swing_highs = []
    swing_lows = []
    
    for i in range(window, len(series) - window):
        # Swing High: Ortadaki değer etrafındakilerden büyük
        if all(series.iloc[i] > series.iloc[i-j] for j in range(1, window+1)) and \
           all(series.iloc[i] > series.iloc[i+j] for j in range(1, window+1)):
            swing_highs.append(i)
        
        # Swing Low: Ortadaki değer etrafındakilerden küçük
        if all(series.iloc[i] < series.iloc[i-j] for j in range(1, window+1)) and \
           all(series.iloc[i] < series.iloc[i+j] for j in range(1, window+1)):
            swing_lows.append(i)
    
    return swing_highs, swing_lows


def detect_rsi_divergence(df: pd.DataFrame, lookback: int = 50) -> Dict:
    """
    RSI-Price divergence tespit et
    
    Bullish Divergence: Fiyat düşük dip yaparken RSI yüksek dip yapıyor
    Bearish Divergence: Fiyat yüksek tepe yaparken RSI düşük tepe yapıyor
    
    Args:
        df: OHLCV + RSI içeren DataFrame
        lookback: Geriye bakış periyodu
    
    Returns:
        Divergence bilgisi dictionary
    """
    if df is None or len(df) < lookback or 'RSI' not in df.columns:
        return {
            'bullish_divergence': False,
            'bearish_divergence': False,
            'signal': None
        }
    
    try:
        recent_df = df.tail(lookback)
        close = recent_df['close']
        rsi = recent_df['RSI']
        
        # Swing noktalarını bul
        price_highs, price_lows = find_swing_points(close, window=3)
        rsi_highs, rsi_lows = find_swing_points(rsi, window=3)
        
        result = {
            'bullish_divergence': False,
            'bearish_divergence': False,
            'signal': None,
            'details': {}
        }
        
        # BULLISH DIVERGENCE: Fiyat lower low, RSI higher low
        if len(price_lows) >= 2 and len(rsi_lows) >= 2:
            # Son iki swing low'u karşılaştır
            recent_price_lows = price_lows[-2:]
            recent_rsi_lows = rsi_lows[-2:]
            
            price_making_lower_low = close.iloc[recent_price_lows[-1]] < close.iloc[recent_price_lows[-2]]
            rsi_making_higher_low = rsi.iloc[recent_rsi_lows[-1]] > rsi.iloc[recent_rsi_lows[-2]]
            
            if price_making_lower_low and rsi_making_higher_low:
                # Divergence tespit edildi
                price_diff = (close.iloc[recent_price_lows[-2]] - close.iloc[recent_price_lows[-1]]) / close.iloc[recent_price_lows[-2]] * 100
                rsi_diff = rsi.iloc[recent_rsi_lows[-1]] - rsi.iloc[recent_rsi_lows[-2]]
                
                # Güç hesaplama
                if rsi_diff > 10 and price_diff > 2:
                    strength = 'strong'
                    confidence = 0.85
                elif rsi_diff > 5 or price_diff > 1:
                    strength = 'moderate'
                    confidence = 0.65
                else:
                    strength = 'weak'
                    confidence = 0.45
                
                result['bullish_divergence'] = True
                result['signal'] = DivergenceSignal(
                    type='bullish',
                    strength=strength,
                    price_trend=-price_diff,
                    indicator_trend=rsi_diff,
                    confidence=confidence,
                    bar_distance=len(recent_df) - recent_price_lows[-1]
                )
                result['details'] = {
                    'price_low_1': close.iloc[recent_price_lows[-2]],
                    'price_low_2': close.iloc[recent_price_lows[-1]],
                    'rsi_low_1': rsi.iloc[recent_rsi_lows[-2]],
                    'rsi_low_2': rsi.iloc[recent_rsi_lows[-1]]
                }
        
        # BEARISH DIVERGENCE: Fiyat higher high, RSI lower high
        if len(price_highs) >= 2 and len(rsi_highs) >= 2 and not result['bullish_divergence']:
            recent_price_highs = price_highs[-2:]
            recent_rsi_highs = rsi_highs[-2:]
            
            price_making_higher_high = close.iloc[recent_price_highs[-1]] > close.iloc[recent_price_highs[-2]]
            rsi_making_lower_high = rsi.iloc[recent_rsi_highs[-1]] < rsi.iloc[recent_rsi_highs[-2]]
            
            if price_making_higher_high and rsi_making_lower_high:
                price_diff = (close.iloc[recent_price_highs[-1]] - close.iloc[recent_price_highs[-2]]) / close.iloc[recent_price_highs[-2]] * 100
                rsi_diff = rsi.iloc[recent_rsi_highs[-2]] - rsi.iloc[recent_rsi_highs[-1]]
                
                if rsi_diff > 10 and price_diff > 2:
                    strength = 'strong'
                    confidence = 0.85
                elif rsi_diff > 5 or price_diff > 1:
                    strength = 'moderate'
                    confidence = 0.65
                else:
                    strength = 'weak'
                    confidence = 0.45
                
                result['bearish_divergence'] = True
                result['signal'] = DivergenceSignal(
                    type='bearish',
                    strength=strength,
                    price_trend=price_diff,
                    indicator_trend=-rsi_diff,
                    confidence=confidence,
                    bar_distance=len(recent_df) - recent_price_highs[-1]
                )
        
        return result
        
    except Exception as e:
        import logging
        logging.warning(f"Divergence detection error: {e}")
        return {
            'bullish_divergence': False,
            'bearish_divergence': False,
            'signal': None
        }


def detect_macd_divergence(df: pd.DataFrame, lookback: int = 50) -> Dict:
    """
    MACD-Price divergence tespit et
    """
    if df is None or len(df) < lookback or 'MACD_Hist' not in df.columns:
        return {'bullish_divergence': False, 'bearish_divergence': False}
    
    try:
        recent_df = df.tail(lookback)
        close = recent_df['close']
        macd_hist = recent_df['MACD_Hist']
        
        # Son 20 bar için basit kontrol
        price_trend = close.iloc[-1] - close.iloc[-20]
        macd_trend = macd_hist.iloc[-1] - macd_hist.iloc[-20]
        
        # Bullish: Fiyat düşerken MACD yükseliyor
        if price_trend < 0 and macd_trend > 0:
            return {
                'bullish_divergence': True,
                'bearish_divergence': False,
                'strength': 'moderate' if abs(macd_trend) > 0.5 else 'weak'
            }
        
        # Bearish: Fiyat yükselirken MACD düşüyor
        if price_trend > 0 and macd_trend < 0:
            return {
                'bullish_divergence': False,
                'bearish_divergence': True,
                'strength': 'moderate' if abs(macd_trend) > 0.5 else 'weak'
            }
        
        return {'bullish_divergence': False, 'bearish_divergence': False}
        
    except Exception:
        return {'bullish_divergence': False, 'bearish_divergence': False}


def get_divergence_score(df: pd.DataFrame) -> Tuple[int, str]:
    """
    Divergence'dan skor ve açıklama döndür
    
    Returns:
        (score, description)
    """
    rsi_div = detect_rsi_divergence(df)
    macd_div = detect_macd_divergence(df)
    
    score = 0
    descriptions = []
    
    if rsi_div.get('bullish_divergence'):
        signal = rsi_div.get('signal')
        if signal:
            if signal.strength == 'strong':
                score += 15
                descriptions.append("🔥 Güçlü RSI Bullish Divergence")
            elif signal.strength == 'moderate':
                score += 10
                descriptions.append("📈 Orta RSI Bullish Divergence")
            else:
                score += 5
                descriptions.append("📊 Zayıf RSI Bullish Divergence")
    
    if macd_div.get('bullish_divergence'):
        if macd_div.get('strength') == 'moderate':
            score += 8
            descriptions.append("📈 MACD Bullish Divergence")
        else:
            score += 4
            descriptions.append("📊 Zayıf MACD Divergence")
    
    # Bearish divergence (uyarı amaçlı, skor düşür)
    if rsi_div.get('bearish_divergence') or macd_div.get('bearish_divergence'):
        score -= 5
        descriptions.append("⚠️ Bearish Divergence Uyarısı")
    
    description = " | ".join(descriptions) if descriptions else "Divergence yok"
    
    return max(score, 0), description
