# analysis/relative_strength.py
import pandas as pd
import numpy as np
from typing import Optional, Dict

def calculate_relative_strength(
    stock_df: pd.DataFrame, 
    benchmark_df: pd.DataFrame, 
    window: int = 50
) -> Dict[str, float]:
    """
    Endekse göre rölatif güç (Comparative Relative Strength) hesaplar.
    
    Args:
        stock_df: Hisse verisi (OHLC)
        benchmark_df: Endeks verisi (OHLC - örn. XU100)
        window: Trend hesaplama periyodu
        
    Returns:
        Dict: {
            'rs_ratio': Fiyat/Endeks oranı,
            'rs_momentum': Oranın değişimi (Alpha),
            'rs_rating': 0-100 arası güç puanı (basitleştirilmiş)
        }
    """
    if stock_df is None or benchmark_df is None:
        return {'rs_score': 0, 'rs_rating': 0}
        
    # Tarihleri eşle (Intersection)
    # Timezone-naive yap (mismatch önlemek için)
    if stock_df.index.tz is not None:
        stock_df.index = stock_df.index.tz_localize(None)
    if benchmark_df.index.tz is not None:
        benchmark_df.index = benchmark_df.index.tz_localize(None)
        
    common_index = stock_df.index.intersection(benchmark_df.index)
    
    if len(common_index) < window:
        return {'rs_score': 0, 'rs_rating': 0}
        
    s_close = stock_df.loc[common_index]['close']
    b_close = benchmark_df.loc[common_index]['close']
    
    # 1. RS Ratio (Hisse / Endeks)
    rs_line = s_close / b_close
    
    # 2. RS Trend (Ratio yükseliyor mu?)
    # Ratio'nun 20 günlük ortalaması
    rs_ma = rs_line.rolling(window=20).mean()
    
    # Şu anki ratio'nun ortalamaya uzaklığı (%)
    current_ratio = rs_line.iloc[-1]
    current_ma = rs_ma.iloc[-1]
    
    rs_momentum = (current_ratio / current_ma - 1) * 100
    
    # 3. Son n gündeki performans farkı (Alpha)
    stock_perf = s_close.pct_change(window).iloc[-1] * 100
    bench_perf = b_close.pct_change(window).iloc[-1] * 100
    alpha = stock_perf - bench_perf
    
    # 4. Basit Puanlama (RS Rating benzeri)
    # Lider hisse tanımı:
    # - RS Line yükseliyor (Momentum > 0)
    # - Alpha pozitif (Endeksi yenmiş)
    
    score = 50  # Başlangıç nötr
    
    if rs_momentum > 0: score += 15
    if rs_momentum > 2: score += 10  # Güçlü momentum
    
    if alpha > 0: score += 15
    if alpha > 10: score += 10  # Ciddi fark atmış
    
    if rs_line.iloc[-1] > rs_line.rolling(50).max().iloc[-1] * 0.98:
        score += 20  # RS Line yeni tepeye yakın (Mansfield RS mantığı)
        
    final_score = min(score, 99)
    
    return {
        'rs_ratio': round(current_ratio, 4),
        'rs_momentum': round(rs_momentum, 2),
        'alpha': round(alpha, 2),
        'rs_score': final_score,
        'rs_rating': final_score  # UI için gerekli key!
    }
