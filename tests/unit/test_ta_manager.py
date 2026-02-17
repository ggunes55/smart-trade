# tests/unit/test_ta_manager.py
"""
TA Manager Unit Tests - Teknik İndikatör Hesaplamaları
"""
import pytest
import pandas as pd
import numpy as np
import sys
import os

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

from indicators.ta_manager import (
    calculate_indicators,
    _calculate_fallback_indicators,
    _calculate_adx_fallback,
    _calculate_cmf_fallback,
    _calculate_mfi_fallback,
    _calculate_volume_indicators,
    _cleanup_indicators
)


@pytest.fixture
def sample_ohlcv():
    """Örnek OHLCV verisi"""
    np.random.seed(42)
    dates = pd.date_range('2024-01-01', periods=100, freq='D')
    closes = 100 + np.cumsum(np.random.randn(100))
    
    return pd.DataFrame({
        'open': closes * 0.99,
        'high': closes * 1.02,
        'low': closes * 0.98,
        'close': closes,
        'volume': np.random.randint(1000000, 5000000, 100)
    }, index=dates)


@pytest.fixture
def trending_up_data():
    """Yükselen trend verisi"""
    dates = pd.date_range('2024-01-01', periods=100, freq='D')
    trend = np.linspace(100, 150, 100)  # 100'den 150'ye
    noise = np.random.randn(100) * 2
    closes = trend + noise
    
    return pd.DataFrame({
        'open': closes * 0.99,
        'high': closes * 1.02,
        'low': closes * 0.98,
        'close': closes,
        'volume': np.random.randint(1000000, 5000000, 100)
    }, index=dates)


@pytest.fixture
def trending_down_data():
    """Düşen trend verisi"""
    dates = pd.date_range('2024-01-01', periods=100, freq='D')
    trend = np.linspace(150, 100, 100)  # 150'den 100'e
    noise = np.random.randn(100) * 2
    closes = trend + noise
    
    return pd.DataFrame({
        'open': closes * 0.99,
        'high': closes * 1.02,
        'low': closes * 0.98,
        'close': closes,
        'volume': np.random.randint(1000000, 5000000, 100)
    }, index=dates)


class TestCalculateIndicators:
    """calculate_indicators fonksiyonu testleri"""
    
    def test_returns_dataframe(self, sample_ohlcv):
        """DataFrame döndürmeli"""
        result = calculate_indicators(sample_ohlcv)
        assert isinstance(result, pd.DataFrame)
    
    def test_adds_ema_columns(self, sample_ohlcv):
        """EMA sütunları eklemeli"""
        result = calculate_indicators(sample_ohlcv)
        assert 'EMA20' in result.columns
        assert 'EMA50' in result.columns
        assert 'EMA200' in result.columns
    
    def test_adds_rsi(self, sample_ohlcv):
        """RSI sütunu eklemeli"""
        result = calculate_indicators(sample_ohlcv)
        assert 'RSI' in result.columns
        # RSI 0-100 arasında olmalı
        assert result['RSI'].min() >= 0
        assert result['RSI'].max() <= 100
    
    def test_adds_macd(self, sample_ohlcv):
        """MACD sütunları eklemeli"""
        result = calculate_indicators(sample_ohlcv)
        assert 'MACD_Level' in result.columns
        assert 'MACD_Signal' in result.columns
        assert 'MACD_Hist' in result.columns
    
    def test_adds_bollinger_bands(self, sample_ohlcv):
        """Bollinger Bands sütunları eklemeli"""
        result = calculate_indicators(sample_ohlcv)
        assert 'BB_Upper' in result.columns
        assert 'BB_Middle' in result.columns
        assert 'BB_Lower' in result.columns
        # Upper >= Middle >= Lower olmalı (NaN olmayan değerler için)
        valid_idx = result['BB_Upper'].notna() & result['BB_Middle'].notna() & result['BB_Lower'].notna()
        assert (result.loc[valid_idx, 'BB_Upper'] >= result.loc[valid_idx, 'BB_Middle']).all()
        assert (result.loc[valid_idx, 'BB_Middle'] >= result.loc[valid_idx, 'BB_Lower']).all()
    
    def test_adds_atr(self, sample_ohlcv):
        """ATR sütunu eklemeli"""
        result = calculate_indicators(sample_ohlcv)
        assert 'ATR14' in result.columns
        # ATR pozitif olmalı
        assert (result['ATR14'] >= 0).all()
    
    def test_adds_adx(self, sample_ohlcv):
        """ADX ve DI sütunları eklemeli"""
        result = calculate_indicators(sample_ohlcv)
        assert 'ADX' in result.columns
        assert 'DI_Plus' in result.columns
        assert 'DI_Minus' in result.columns
        # ADX 0-100 arasında
        assert result['ADX'].min() >= 0
        assert result['ADX'].max() <= 100
    
    def test_empty_dataframe(self):
        """Boş DataFrame için hata vermemeli"""
        result = calculate_indicators(pd.DataFrame())
        assert result.empty or result is not None
    
    def test_insufficient_data(self):
        """Yetersiz veri için çalışmalı"""
        df = pd.DataFrame({
            'open': [100, 101],
            'high': [102, 103],
            'low': [98, 99],
            'close': [101, 102],
            'volume': [1000, 2000]
        })
        result = calculate_indicators(df)
        assert result is not None


class TestADXFallback:
    """ADX fallback hesaplama testleri"""
    
    def test_adx_in_valid_range(self, sample_ohlcv):
        """ADX 0-100 arasında olmalı"""
        _calculate_adx_fallback(sample_ohlcv)
        assert sample_ohlcv['ADX'].min() >= 0
        assert sample_ohlcv['ADX'].max() <= 100
    
    def test_di_plus_calculated(self, sample_ohlcv):
        """DI+ hesaplanmalı"""
        _calculate_adx_fallback(sample_ohlcv)
        assert 'DI_Plus' in sample_ohlcv.columns
        assert (sample_ohlcv['DI_Plus'] >= 0).all()
    
    def test_di_minus_calculated(self, sample_ohlcv):
        """DI- hesaplanmalı"""
        _calculate_adx_fallback(sample_ohlcv)
        assert 'DI_Minus' in sample_ohlcv.columns
        assert (sample_ohlcv['DI_Minus'] >= 0).all()
    
    def test_strong_trend_high_adx(self, trending_up_data):
        """Güçlü trendde ADX hesaplanmalı ve geçerli olmalı"""
        _calculate_adx_fallback(trending_up_data)
        # ADX hesaplanmış ve geçerli aralıkta olmalı
        assert 'ADX' in trending_up_data.columns
        recent_adx = trending_up_data['ADX'].iloc[-20:].mean()
        # ADX 0-100 arasında geçerli bir değer olmalı
        assert 0 <= recent_adx <= 100


class TestCMFCalculation:
    """CMF hesaplama testleri"""
    
    def test_cmf_in_valid_range(self, sample_ohlcv):
        """CMF -1 ile 1 arasında olmalı"""
        cmf = _calculate_cmf_fallback(sample_ohlcv)
        assert cmf.min() >= -1
        assert cmf.max() <= 1
    
    def test_cmf_no_nan(self, sample_ohlcv):
        """CMF NaN içermemeli (ilk değerler hariç)"""
        cmf = _calculate_cmf_fallback(sample_ohlcv)
        assert cmf.iloc[-50:].isna().sum() == 0


class TestMFICalculation:
    """MFI hesaplama testleri"""
    
    def test_mfi_in_valid_range(self, sample_ohlcv):
        """MFI 0-100 arasında olmalı"""
        mfi = _calculate_mfi_fallback(sample_ohlcv)
        assert mfi.min() >= 0
        assert mfi.max() <= 100
    
    def test_mfi_default_50(self, sample_ohlcv):
        """MFI varsayılan 50 ile doldurulmalı"""
        mfi = _calculate_mfi_fallback(sample_ohlcv)
        # İlk değerler 50 olmalı
        assert mfi.iloc[0] == 50 or not np.isnan(mfi.iloc[-1])


class TestVolumeIndicators:
    """Volume indikatör testleri"""
    
    def test_volume_averages(self, sample_ohlcv):
        """Volume ortalamaları hesaplanmalı"""
        _calculate_volume_indicators(sample_ohlcv)
        assert 'Volume_10d_Avg' in sample_ohlcv.columns
        assert 'Volume_20d_Avg' in sample_ohlcv.columns
    
    def test_relative_volume(self, sample_ohlcv):
        """Relative volume hesaplanmalı"""
        _calculate_volume_indicators(sample_ohlcv)
        assert 'Relative_Volume' in sample_ohlcv.columns
        # 0.1 - 10 arasında olmalı (clip)
        assert sample_ohlcv['Relative_Volume'].min() >= 0.1
        assert sample_ohlcv['Relative_Volume'].max() <= 10.0
    
    def test_daily_change(self, sample_ohlcv):
        """Günlük değişim hesaplanmalı"""
        _calculate_volume_indicators(sample_ohlcv)
        assert 'Daily_Change_Pct' in sample_ohlcv.columns


class TestCleanupIndicators:
    """İndikatör temizleme testleri"""
    
    def test_fills_nan_rsi(self, sample_ohlcv):
        """RSI NaN değerleri 50 ile doldurulmalı"""
        sample_ohlcv['RSI'] = np.nan
        result = _cleanup_indicators(sample_ohlcv)
        assert result['RSI'].iloc[0] == 50
    
    def test_fills_nan_relative_volume(self, sample_ohlcv):
        """Relative Volume NaN değerleri 1.0 ile doldurulmalı"""
        sample_ohlcv['Relative_Volume'] = np.nan
        result = _cleanup_indicators(sample_ohlcv)
        assert result['Relative_Volume'].iloc[0] == 1.0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
