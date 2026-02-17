import pytest
import pandas as pd
import numpy as np
from analysis.risk_metrics import calculate_risk_metrics
from analysis.swing_quality import calculate_swing_quality
from analysis.trend_score import calculate_advanced_trend_score

@pytest.fixture
def sample_data():
    # Create a 200-day sample data with a trend
    dates = pd.date_range(start='2024-01-01', periods=200)
    
    # Create a nice uptrend with some noise
    np.random.seed(42)
    noise = np.random.normal(0, 1, 200)
    trend = np.linspace(10, 20, 200) # From 10 to 20
    prices = trend + noise
    
    # Ensure no negative prices
    prices = np.maximum(prices, 0.1)
    
    df = pd.DataFrame({
        'open': prices,
        'high': prices * 1.02,
        'low': prices * 0.98,
        'close': prices,
        'volume': np.random.randint(1000, 10000, 200)
    }, index=dates)
    
    # Add indicators needed for trend_score
    df['EMA20'] = df['close'].ewm(span=20).mean()
    df['EMA50'] = df['close'].ewm(span=50).mean()
    df['EMA200'] = df['close'].ewm(span=200).mean()
    df['RSI'] = 60 # Dummy
    df['MACD_Level'] = 1
    df['MACD_Signal'] = 0.5
    df['MACD_Hist'] = 0.5
    df['Relative_Volume'] = 1.5
    df['OBV'] = 100000
    df['OBV_EMA'] = 90000
    df['ADX'] = 25
    df['DI_Plus'] = 30
    df['DI_Minus'] = 10
    
    return df

def test_risk_metrics(sample_data):
    metrics = calculate_risk_metrics(sample_data)
    
    assert metrics is not None
    assert 'sharpe_ratio' in metrics
    assert 'volatility_score' in metrics
    assert 'max_drawdown' in metrics
    
    print(f"\nRisk Metrics: {metrics}")
    
    # Sharpe should be positive for this uptrend
    assert metrics['sharpe_ratio'] > 0

def test_swing_quality(sample_data):
    quality = calculate_swing_quality(sample_data)
    
    assert quality is not None
    assert 'efficiency_ratio' in quality
    
    print(f"\nQuality Metrics: {quality}")
    
    # Efficiency should be decent
    assert quality['efficiency_ratio'] > 0

def test_composite_score(sample_data):
    config = {
        'ema_weight': 0.25,
        'rsi_weight': 0.20,
        'macd_weight': 0.15,
        'volume_weight': 0.15,
        'adx_weight': 0.10,
        'pa_weight': 0.10,
        'regime_weight': 0.05,
        'min_total_score': 50
    }
    
    result = calculate_advanced_trend_score(sample_data, "TEST", config)
    
    assert result is not None
    assert result['passed'] is True
    assert 'risk_metrics' in result
    assert 'quality_metrics' in result
    
    print(f"\nTotal Score: {result['total_score']}")
    print(f"Risk Component: {result['risk_metrics']}")


# --- Yeni test: Rolling correlation ---
def test_rolling_correlation(sample_data):
    # Endeks verisi ekle
    sample_data = sample_data.copy()
    # Endeks ile yüksek korelasyon: close + küçük gürültü
    sample_data['benchmark_close'] = sample_data['close'] + np.random.normal(0, 0.5, len(sample_data))
    config = {
        'ema_weight': 0.25,
        'rsi_weight': 0.20,
        'macd_weight': 0.15,
        'volume_weight': 0.15,
        'adx_weight': 0.10,
        'pa_weight': 0.10,
        'regime_weight': 0.05,
        'min_total_score': 50
    }
    result = calculate_advanced_trend_score(sample_data, "TEST", config)
    # Rolling correlation skoru ve detayları kontrol et
    found = False
    for comp in result['components']:
        if comp['category'].startswith('Rolling Correlation'):
            found = True
            assert 'rolling_corr' in comp['details']
            print(f"Rolling Corr: {comp['details']['rolling_corr']}")
    assert found, "Rolling correlation skoru bulunmalı"
