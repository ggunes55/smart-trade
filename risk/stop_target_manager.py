# risk/stop_target_manager.py
"""
Stop-Loss ve Hedef Fiyat Yönetim Modülü

Bu modül, ATR (Average True Range) bazlı dinamik stop-loss ve
Target seviyelerini hesaplar. Fibonacci ve Bollinger Band entegrasyonu içerir.
"""
import pandas as pd
import numpy as np
from typing import Tuple, Optional, Dict


def _calculate_stops_targets(
    df: pd.DataFrame, 
    symbol: str, 
    config: Dict
) -> Tuple[Optional[float], Optional[float], Optional[float]]:
    """
    Dinamik stop-loss ve hedef seviyelerini ATR bazlı belirler.
    
    Hesaplama Metodolojisi:
    1. Stop-Loss = Kapanış - (ATR × stop_multiplier)
    2. Hedef 1 = Kapanış + (Risk × min_risk_reward_ratio)
    3. Hedef 2 = Hedef 1 × 1.5
    
    Alternatif olarak Bollinger üst bandı hedef olarak kullanılabilir.
    
    Args:
        df: OHLCV + ATR14 içeren DataFrame
        symbol: Hisse sembolü (loglama için)
        config: Konfigürasyon dictionary'si
            - stop_multiplier: ATR çarpanı (varsayılan: 1.5)
            - min_risk_reward_ratio: Min R/R oranı (varsayılan: 2.0)
    
    Returns:
        Tuple: (stop_loss, target1, target2)
        - Hata durumunda (None, None, None)
    
    Example:
        >>> config = {'stop_multiplier': 1.5, 'min_risk_reward_ratio': 2.0}
        >>> stop, t1, t2 = _calculate_stops_targets(df, 'GARAN', config)
        >>> print(f"Stop: {stop}, Hedef1: {t1}, Hedef2: {t2}")
        Stop: 95.5, Hedef1: 109.0, Hedef2: 115.75
    
    Note:
        ATR14 sütununun mevcut olması gerekir. Yoksa fallback hesaplama yapılır.
    """
    if df is None or df.empty:
        return None, None, None

    latest = df.iloc[-1]
    high = latest['high']
    low = latest['low']
    close = latest['close']
    
    # ATR değeri - fallback ile
    if 'ATR14' in df.columns:
        atr = latest['ATR14']
    else:
        atr = (high - low) * 0.1  # Fallback: Range'in %10'u
        
    atr = max(atr, 0.01)  # Min ATR koruması

    # Stop-loss: ATR tabanlı
    stop_multiplier = config.get('stop_multiplier', 1.5)
    stop_loss = close - (atr * stop_multiplier)
    stop_loss = max(stop_loss, low - (atr * 0.5))  # Dip koruması

    # Hedefler: Risk/Reward oranına göre
    rr1 = config.get('min_risk_reward_ratio', 2.0)
    rr2 = rr1 * 1.5

    risk_dist = close - stop_loss
    if risk_dist <= 0:
        return None, None, None

    target1 = close + (risk_dist * rr1)
    target2 = close + (risk_dist * rr2)

    # Alternatif: Bollinger üst bandı kullan (varsa)
    if 'BB_Upper' in df.columns:
        bb_upper = df['BB_Upper'].iloc[-1]
        if pd.notna(bb_upper) and bb_upper > target1:
            target1 = min(bb_upper, target1 * 1.2)
            target2 = target1 * 1.3

    return float(stop_loss), float(target1), float(target2)


def calculate_trailing_stop(
    current_price: float,
    entry_price: float,
    current_stop: float,
    atr: float,
    trailing_atr_multiplier: float = 2.0
) -> float:
    """
    Trailing (iz süren) stop seviyesini hesaplar.
    
    Stop sadece kâr yönünde hareket eder, asla geri gitmez.
    
    Args:
        current_price: Mevcut piyasa fiyatı
        entry_price: Giriş fiyatı
        current_stop: Mevcut stop seviyesi
        atr: ATR değeri
        trailing_atr_multiplier: Stop mesafesi için ATR çarpanı
    
    Returns:
        Yeni stop seviyesi (mevcut stop'tan düşük olamaz)
    """
    # En son yüksek fiyattan ATR kadar aşağıda
    new_stop = current_price - (atr * trailing_atr_multiplier)
    
    # Stop sadece yukarı hareket edebilir
    if new_stop > current_stop:
        return new_stop
    
    return current_stop


def calculate_multi_level_exit(
    entry_price: float,
    risk_distance: float,
    num_levels: int = 3,
    scaling_factor: float = 0.5
) -> Dict:
    """
    Çok seviyeli çıkış stratejisi: Risk porsiyonlaması + Trailing
    
    Strateji:
    Level 1: +1R @ %50 kâr (Pozisyon %33'ü kapat, SL = Entry)
    Level 2: +2R @ +%100 kâr (Pozisyon %33'ü kapat, SL = +0.5R)
    Level 3: +3R+Trailing (Kalan %33, Trailing SL)
    
    Args:
        entry_price: Giriş fiyatı
        risk_distance: Stop-Loss'a kadar olan mesafe (Risk miktarı)
        num_levels: Çıkış seviyeleri (default: 3)
        scaling_factor: Seviyeler arası kâr artış faktörü
    
    Returns:
        Dict: Seviye bilgileri
        {
            'level_1': {'target': fiyat, 'exit_pct': 33.3, 'stop_loss': entry_price},
            'level_2': {'target': fiyat, 'exit_pct': 33.3, 'stop_loss': entry+0.5R},
            'level_3': {'target': fiyat, 'exit_pct': 33.3, 'stop_loss': 'trailing'}
        }
    """
    if risk_distance <= 0:
        return {}
    
    levels = {}
    position_per_level = 100 / num_levels
    
    for i in range(1, num_levels + 1):
        profit_target = i * scaling_factor * risk_distance
        target_price = entry_price + profit_target
        
        if i == 1:
            stop_loss = entry_price  # Break-even
        elif i == 2:
            stop_loss = entry_price + (0.5 * risk_distance)  # +0.5R
        else:
            stop_loss = "trailing"  # Son seviye: Trailing SL
        
        levels[f'level_{i}'] = {
            'target': float(round(target_price, 2)),
            'profit_r': float(i * scaling_factor),  # Kâr R cinsinden
            'exit_pct': float(round(position_per_level, 1)),  # Pozisyon %'si
            'stop_loss': stop_loss,
            'description': f"Seviyeleri kapat %{round(position_per_level)}, Target: {i}R"
        }
    
    return levels
