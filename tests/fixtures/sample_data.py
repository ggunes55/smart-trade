# -*- coding: utf-8 -*-
"""Sample data for tests"""
import pandas as pd
import numpy as np

def create_sample_stock_data(days=100, trend='bullish'):
    """Örnek hisse verisi oluştur"""
    dates = pd.date_range('2024-01-01', periods=days, freq='D')
    base_price = 100
    
    if trend == 'bullish':
        trend_component = np.linspace(0, 20, days)
    elif trend == 'bearish':
        trend_component = np.linspace(0, -20, days)
    else:
        trend_component = np.zeros(days)
    
    noise = np.random.normal(0, 2, days)
    closes = base_price + trend_component + noise
    
    df = pd.DataFrame({
        'datetime': dates,
        'open': closes * 0.99,
        'high': closes * 1.02,
        'low': closes * 0.98,
        'close': closes,
        'volume': np.random.randint(1000000, 5000000, days)
    })
    df.set_index('datetime', inplace=True)
    return df
