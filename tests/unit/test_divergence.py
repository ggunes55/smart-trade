# tests/unit/test_divergence.py
"""
Divergence Detection Unit Tests
"""
import pytest
import pandas as pd
import numpy as np
import sys
import os

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

from analysis.divergence import (
    detect_rsi_divergence,
    detect_macd_divergence,
    get_divergence_score,
    find_swing_points,
    DivergenceSignal
)


@pytest.fixture
def bullish_divergence_data():
    """
    Bullish divergence senaryosu:
    - Fiyat düşük dip yapıyor (lower low)
    - RSI yüksek dip yapıyor (higher low)
    """
    np.random.seed(42)
    dates = pd.date_range('2024-01-01', periods=100, freq='D')
    
    # Fiyat: İlk 50 bar düşüş, sonra daha düşük dip
    prices = np.concatenate([
        np.linspace(100, 80, 30),  # Düşüş
        np.linspace(80, 90, 20),   # Toparlanma
        np.linspace(90, 75, 30),   # Daha düşük dip
        np.linspace(75, 85, 20)    # Toparlanma
    ])
    
    # RSI: İlk dipte 25, ikinci dipte 35 (higher low)
    rsi = np.concatenate([
        np.linspace(50, 25, 30),  # Düşük RSI
        np.linspace(25, 45, 20),  # Toparlanma
        np.linspace(45, 35, 30),  # Daha yüksek dip (divergence!)
        np.linspace(35, 50, 20)   # Toparlanma
    ])
    
    return pd.DataFrame({
        'open': prices * 0.99,
        'high': prices * 1.02,
        'low': prices * 0.98,
        'close': prices,
        'RSI': rsi,
        'MACD_Hist': np.random.randn(100) * 0.5,
        'volume': np.random.randint(1000000, 5000000, 100)
    }, index=dates)


@pytest.fixture
def bearish_divergence_data():
    """
    Bearish divergence senaryosu:
    - Fiyat yüksek tepe yapıyor (higher high)
    - RSI düşük tepe yapıyor (lower high)
    """
    np.random.seed(123)
    dates = pd.date_range('2024-01-01', periods=100, freq='D')
    
    prices = np.concatenate([
        np.linspace(100, 120, 30),
        np.linspace(120, 110, 20),
        np.linspace(110, 130, 30),  # Daha yüksek tepe
        np.linspace(130, 120, 20)
    ])
    
    rsi = np.concatenate([
        np.linspace(50, 75, 30),    # Yüksek RSI
        np.linspace(75, 55, 20),
        np.linspace(55, 65, 30),    # Daha düşük tepe (divergence!)
        np.linspace(65, 50, 20)
    ])
    
    return pd.DataFrame({
        'open': prices * 0.99,
        'high': prices * 1.02,
        'low': prices * 0.98,
        'close': prices,
        'RSI': rsi,
        'MACD_Hist': np.random.randn(100) * 0.5,
        'volume': np.random.randint(1000000, 5000000, 100)
    }, index=dates)


@pytest.fixture
def no_divergence_data():
    """Divergence olmayan normal trend"""
    np.random.seed(456)
    dates = pd.date_range('2024-01-01', periods=100, freq='D')
    
    prices = np.linspace(100, 150, 100) + np.random.randn(100) * 2
    rsi = np.linspace(40, 70, 100) + np.random.randn(100) * 5
    rsi = np.clip(rsi, 0, 100)
    
    return pd.DataFrame({
        'open': prices * 0.99,
        'high': prices * 1.02,
        'low': prices * 0.98,
        'close': prices,
        'RSI': rsi,
        'MACD_Hist': np.linspace(-0.5, 0.5, 100),
        'volume': np.random.randint(1000000, 5000000, 100)
    }, index=dates)


class TestFindSwingPoints:
    """Swing point tespit testleri"""
    
    def test_finds_swing_highs(self):
        """Swing high noktalarını bulmalı"""
        series = pd.Series([1, 2, 3, 4, 5, 4, 3, 2, 3, 4, 5, 6, 5, 4])
        highs, lows = find_swing_points(series, window=2)
        assert len(highs) > 0
    
    def test_finds_swing_lows(self):
        """Swing low noktalarını bulmalı"""
        series = pd.Series([5, 4, 3, 2, 1, 2, 3, 4, 3, 2, 1, 0, 1, 2])
        highs, lows = find_swing_points(series, window=2)
        assert len(lows) > 0
    
    def test_short_series_empty(self):
        """Kısa seri için boş dönmeli"""
        series = pd.Series([1, 2, 3])
        highs, lows = find_swing_points(series, window=3)
        assert len(highs) == 0
        assert len(lows) == 0


class TestDetectRSIDivergence:
    """RSI divergence tespit testleri"""
    
    def test_returns_dict(self, bullish_divergence_data):
        """Dictionary döndürmeli"""
        result = detect_rsi_divergence(bullish_divergence_data)
        assert isinstance(result, dict)
    
    def test_contains_required_keys(self, bullish_divergence_data):
        """Gerekli anahtarları içermeli"""
        result = detect_rsi_divergence(bullish_divergence_data)
        assert 'bullish_divergence' in result
        assert 'bearish_divergence' in result
    
    def test_none_input(self):
        """None input için False döndürmeli"""
        result = detect_rsi_divergence(None)
        assert result['bullish_divergence'] == False
        assert result['bearish_divergence'] == False
    
    def test_missing_rsi_column(self):
        """RSI sütunu yoksa False döndürmeli"""
        df = pd.DataFrame({'close': [1, 2, 3]})
        result = detect_rsi_divergence(df)
        assert result['bullish_divergence'] == False


class TestDetectMACDDivergence:
    """MACD divergence testleri"""
    
    def test_returns_dict(self, bullish_divergence_data):
        """Dictionary döndürmeli"""
        result = detect_macd_divergence(bullish_divergence_data)
        assert isinstance(result, dict)
    
    def test_missing_macd(self):
        """MACD yoksa False döndürmeli"""
        df = pd.DataFrame({'close': range(100)})
        result = detect_macd_divergence(df)
        assert result['bullish_divergence'] == False


class TestGetDivergenceScore:
    """Divergence skor testleri"""
    
    def test_returns_tuple(self, bullish_divergence_data):
        """Tuple döndürmeli (score, description)"""
        result = get_divergence_score(bullish_divergence_data)
        assert isinstance(result, tuple)
        assert len(result) == 2
    
    def test_score_non_negative(self, bullish_divergence_data):
        """Skor negatif olmamalı"""
        score, _ = get_divergence_score(bullish_divergence_data)
        assert score >= 0
    
    def test_no_divergence_zero_score(self, no_divergence_data):
        """Divergence yoksa skor 0 olabilir"""
        score, _ = get_divergence_score(no_divergence_data)
        # Skor 0 veya düşük olmalı
        assert score <= 5


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
