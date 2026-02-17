# analysis/beta.py
"""
Beta Hesaplama Modülü

Beta, bir hissenin piyasaya göre volatilitesini ölçer:
- Beta = 1.0: Piyasa ile aynı hareket
- Beta > 1.0: Piyasadan daha volatil (agresif)
- Beta < 1.0: Piyasadan daha az volatil (defansif)
- Beta < 0: Piyasa ile ters hareket (nadir)

Swing trading için beta önemlidir çünkü:
- Yüksek beta hisseler daha geniş fiyat hareketleri yapar
- Düşük beta hisseler daha az risk taşır
"""
import pandas as pd
import numpy as np
from typing import Dict, Optional, Tuple
import logging

logger = logging.getLogger(__name__)


def calculate_beta(
    stock_df: pd.DataFrame,
    benchmark_df: pd.DataFrame,
    period: int = 252,
    min_periods: int = 60
) -> Dict[str, float]:
    """
    Hisse senedinin piyasaya göre beta değerini hesaplar.
    
    Formül: Beta = Cov(Stock, Market) / Var(Market)
    
    Args:
        stock_df: Hisse OHLCV verisi (close sütunu gerekli)
        benchmark_df: Endeks OHLCV verisi (close sütunu gerekli)
        period: Hesaplama periyodu (gün, varsayılan 252 = 1 yıl)
        min_periods: Minimum gerekli veri sayısı
    
    Returns:
        Dict: {
            'beta': Beta değeri,
            'correlation': Korelasyon katsayısı,
            'r_squared': R-kare değeri,
            'alpha': Jensen's Alpha (yıllık),
            'volatility_ratio': Hisse vol / Piyasa vol
        }
    
    Example:
        >>> result = calculate_beta(stock_df, xu100_df, period=252)
        >>> print(f"Beta: {result['beta']:.2f}")
        Beta: 1.35
    """
    if stock_df is None or benchmark_df is None:
        return _empty_beta_result()
    
    if len(stock_df) < min_periods or len(benchmark_df) < min_periods:
        logger.warning(f"Yetersiz veri: stock={len(stock_df)}, benchmark={len(benchmark_df)}")
        return _empty_beta_result()
    
    try:
        # Tarihleri eşle
        common_index = stock_df.index.intersection(benchmark_df.index)
        if len(common_index) < min_periods:
            return _empty_beta_result()
        
        # Son N günü al
        common_index = common_index[-period:] if len(common_index) > period else common_index
        
        stock_close = stock_df.loc[common_index]['close']
        bench_close = benchmark_df.loc[common_index]['close']
        
        # Günlük getiriler
        stock_returns = stock_close.pct_change().dropna()
        bench_returns = bench_close.pct_change().dropna()
        
        if len(stock_returns) < min_periods - 1:
            return _empty_beta_result()
        
        # Beta hesaplama (Covariance / Variance)
        covariance = stock_returns.cov(bench_returns)
        variance = bench_returns.var()
        
        if variance <= 0:
            return _empty_beta_result()
        
        beta = covariance / variance
        
        # Korelasyon
        correlation = stock_returns.corr(bench_returns)
        r_squared = correlation ** 2
        
        # Alpha (Jensen's Alpha) - Yıllık
        stock_annual = stock_returns.mean() * 252
        bench_annual = bench_returns.mean() * 252
        risk_free_rate = 0.0  # Basitlik için 0
        alpha = stock_annual - (risk_free_rate + beta * (bench_annual - risk_free_rate))
        
        # Volatilite oranı
        stock_vol = stock_returns.std() * np.sqrt(252)
        bench_vol = bench_returns.std() * np.sqrt(252)
        vol_ratio = stock_vol / bench_vol if bench_vol > 0 else 1.0
        
        return {
            'beta': round(float(beta), 3),
            'correlation': round(float(correlation), 3),
            'r_squared': round(float(r_squared), 3),
            'alpha': round(float(alpha * 100), 2),  # Yüzde olarak
            'volatility_ratio': round(float(vol_ratio), 3),
            'stock_volatility': round(float(stock_vol * 100), 2),
            'benchmark_volatility': round(float(bench_vol * 100), 2),
            'data_points': len(stock_returns)
        }
        
    except Exception as e:
        logger.error(f"Beta hesaplama hatası: {e}")
        return _empty_beta_result()


def _empty_beta_result() -> Dict[str, float]:
    """Boş beta sonucu döndür"""
    return {
        'beta': 1.0,  # Varsayılan nötr beta
        'correlation': 0.0,
        'r_squared': 0.0,
        'alpha': 0.0,
        'volatility_ratio': 1.0,
        'stock_volatility': 0.0,
        'benchmark_volatility': 0.0,
        'data_points': 0
    }


def calculate_rolling_beta(
    stock_df: pd.DataFrame,
    benchmark_df: pd.DataFrame,
    window: int = 60
) -> pd.Series:
    """
    Kayan pencere ile beta hesaplar (trend analizi için).
    
    Args:
        stock_df: Hisse verisi
        benchmark_df: Endeks verisi
        window: Kayan pencere boyutu (gün)
    
    Returns:
        pd.Series: Tarihlere göre beta değerleri
    """
    if stock_df is None or benchmark_df is None:
        return pd.Series()
    
    try:
        common_index = stock_df.index.intersection(benchmark_df.index)
        if len(common_index) < window:
            return pd.Series()
        
        stock_returns = stock_df.loc[common_index]['close'].pct_change()
        bench_returns = benchmark_df.loc[common_index]['close'].pct_change()
        
        # Rolling covariance ve variance
        rolling_cov = stock_returns.rolling(window=window).cov(bench_returns)
        rolling_var = bench_returns.rolling(window=window).var()
        
        rolling_beta = rolling_cov / rolling_var
        return rolling_beta.dropna()
        
    except Exception as e:
        logger.error(f"Rolling beta hatası: {e}")
        return pd.Series()


def get_beta_classification(beta: float) -> Tuple[str, str]:
    """
    Beta değerine göre sınıflandırma yapar.
    
    Args:
        beta: Beta değeri
    
    Returns:
        Tuple: (kategori, açıklama)
    """
    if beta < 0:
        return "Negatif", "⚡ Piyasa ile ters hareket - çok nadir"
    elif beta < 0.5:
        return "Çok Düşük", "🛡️ Defansif - düşük risk"
    elif beta < 0.8:
        return "Düşük", "🔵 Piyasadan daha stabil"
    elif beta < 1.0:
        return "Nötr-Düşük", "⚪ Piyasaya yakın ama daha az volatil"
    elif beta < 1.2:
        return "Nötr-Yüksek", "⚪ Piyasaya yakın"
    elif beta < 1.5:
        return "Yüksek", "🔴 Agresif - daha fazla hareket"
    else:
        return "Çok Yüksek", "🔥 Çok volatil - yüksek risk/ödül"


def get_beta_adjusted_position(
    base_position_size: int,
    beta: float,
    target_beta: float = 1.0
) -> int:
    """
    Beta'ya göre pozisyon boyutunu ayarlar.
    
    Yüksek beta hisseler için daha küçük pozisyon,
    düşük beta hisseler için daha büyük pozisyon.
    
    Args:
        base_position_size: Temel pozisyon boyutu
        beta: Hissenin beta değeri
        target_beta: Hedef portföy betası
    
    Returns:
        Ayarlanmış pozisyon boyutu
    """
    if beta <= 0:
        return base_position_size
    
    # Beta adjustment factor
    adjustment = target_beta / beta
    
    # Sınırla: 0.5x - 2x arası
    adjustment = max(0.5, min(2.0, adjustment))
    
    adjusted_size = int(base_position_size * adjustment)
    return max(1, adjusted_size)
