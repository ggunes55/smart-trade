# -*- coding: utf-8 -*-
"""
Optimized Support/Resistance Detection using scipy
Vektörel ve hızlı destek/direnç tespiti
"""
import numpy as np
import pandas as pd
from typing import Dict, List, Tuple, Optional
import logging

logger = logging.getLogger(__name__)

try:
    from scipy.signal import argrelextrema
    SCIPY_AVAILABLE = True
except ImportError:
    logger.warning("scipy not found. Using fallback S/R detection.")
    SCIPY_AVAILABLE = False


def find_support_resistance_vectorized(df: pd.DataFrame, order: int = 5, 
                                       max_levels: int = 5) -> Dict[str, List[float]]:
    """
    Vektörel destek/direnç tespiti - scipy kullanarak O(N)
    
    Args:
        df: OHLCV DataFrame
        order: Lokal extrema için bakılacak bar sayısı (her iki yönde)
        max_levels: Döndürülecek maksimum seviye sayısı
        
    Returns:
        {'supports': [seviye1, seviye2, ...], 'resistances': [seviye1, seviye2, ...]}
    """
    if not SCIPY_AVAILABLE or df is None or df.empty or len(df) < order * 2:
        return {'supports': [], 'resistances': []}
    
    try:
        highs = df['high'].values
        lows = df['low'].values
        current_price = df['close'].iloc[-1]
        
        # Lokal maksimum ve minimumları bul - O(N) karmaşıklık
        resistance_idx = argrelextrema(highs, np.greater, order=order)[0]
        support_idx = argrelextrema(lows, np.less, order=order)[0]
        
        # Seviyeleri al
        resistance_levels = highs[resistance_idx] if len(resistance_idx) > 0 else np.array([])
        support_levels = lows[support_idx] if len(support_idx) > 0 else np.array([])
        
        # Mevcut fiyata göre filtrele ve sırala
        # Dirençler: fiyatın üzeri, en yakından en uzağa
        valid_resistances = resistance_levels[resistance_levels > current_price]
        sorted_resistances = np.sort(valid_resistances)[:max_levels]
        
        # Destekler: fiyatın altı, en yakından en uzağa (büyükten küçüğe sırala)
        valid_supports = support_levels[support_levels < current_price]
        sorted_supports = np.sort(valid_supports)[::-1][:max_levels]
        
        return {
            'supports': sorted_supports.tolist(),
            'resistances': sorted_resistances.tolist()
        }
        
    except Exception as e:
        logger.error(f"S/R detection error: {e}")
        return {'supports': [], 'resistances': []}


def find_pivot_points(df: pd.DataFrame) -> Dict[str, float]:
    """
    Standart pivot points hesaplama
    
    Returns:
        {'pivot': P, 'r1': R1, 'r2': R2, 'r3': R3, 's1': S1, 's2': S2, 's3': S3}
    """
    if df is None or df.empty or len(df) < 2:
        return {}
    
    try:
        prev = df.iloc[-2]
        high = prev['high']
        low = prev['low']
        close = prev['close']
        
        pivot = (high + low + close) / 3
        
        r1 = 2 * pivot - low
        s1 = 2 * pivot - high
        r2 = pivot + (high - low)
        s2 = pivot - (high - low)
        r3 = pivot + 2 * (high - low)
        s3 = pivot - 2 * (high - low)
        
        return {
            'pivot': round(pivot, 2),
            'r1': round(r1, 2),
            'r2': round(r2, 2),
            'r3': round(r3, 2),
            's1': round(s1, 2),
            's2': round(s2, 2),
            's3': round(s3, 2)
        }
        
    except Exception as e:
        logger.error(f"Pivot calculation error: {e}")
        return {}


def cluster_levels(levels: List[float], tolerance_pct: float = 0.5) -> List[float]:
    """
    Yakın seviyeleri grupla (cluster)
    
    Args:
        levels: Seviye listesi
        tolerance_pct: Gruplama toleransı (%)
        
    Returns:
        Gruplanmış seviyeler
    """
    if not levels:
        return []
    
    sorted_levels = sorted(levels)
    clusters = []
    current_cluster = [sorted_levels[0]]
    
    for level in sorted_levels[1:]:
        # Önceki seviyeye yakınsa aynı gruba ekle
        if current_cluster and abs(level - current_cluster[-1]) / current_cluster[-1] * 100 < tolerance_pct:
            current_cluster.append(level)
        else:
            # Yeni gruba geç
            clusters.append(np.mean(current_cluster))
            current_cluster = [level]
    
    # Son grubu ekle
    if current_cluster:
        clusters.append(np.mean(current_cluster))
    
    return [round(c, 2) for c in clusters]


def get_nearby_levels(current_price: float, levels: Dict[str, List[float]], 
                     threshold_pct: float = 3.0) -> Dict[str, Optional[float]]:
    """
    Fiyata yakın destek/direnç seviyelerini bul
    
    Args:
        current_price: Mevcut fiyat
        levels: {'supports': [...], 'resistances': [...]}
        threshold_pct: Yakınlık eşiği (%)
        
    Returns:
        {'nearest_support': level, 'nearest_resistance': level}
    """
    result = {'nearest_support': None, 'nearest_resistance': None}
    
    supports = levels.get('supports', [])
    resistances = levels.get('resistances', [])
    
    # En yakın desteği bul
    for support in supports:
        distance_pct = (current_price - support) / current_price * 100
        if 0 < distance_pct <= threshold_pct:
            result['nearest_support'] = support
            break
    
    # En yakın direnci bul
    for resistance in resistances:
        distance_pct = (resistance - current_price) / current_price * 100
        if 0 < distance_pct <= threshold_pct:
            result['nearest_resistance'] = resistance
            break
    
    return result
