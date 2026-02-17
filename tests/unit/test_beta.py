# tests/unit/test_beta.py
"""
Beta Calculation Unit Tests
"""
import pytest
import pandas as pd
import numpy as np
import sys
import os

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

from analysis.beta import (
    calculate_beta,
    calculate_rolling_beta,
    get_beta_classification,
    get_beta_adjusted_position,
    _empty_beta_result
)


@pytest.fixture
def market_data():
    """Piyasa (endeks) verisi"""
    np.random.seed(42)
    dates = pd.date_range('2024-01-01', periods=300, freq='D')
    returns = np.random.randn(300) * 0.01  # %1 günlük volatilite
    closes = 100 * np.cumprod(1 + returns)
    
    return pd.DataFrame({
        'open': closes * 0.99,
        'high': closes * 1.01,
        'low': closes * 0.99,
        'close': closes,
        'volume': np.random.randint(10000000, 50000000, 300)
    }, index=dates)


@pytest.fixture
def high_beta_stock(market_data):
    """Yüksek beta hisse (piyasadan 1.5x volatil)"""
    np.random.seed(123)
    market_returns = market_data['close'].pct_change().fillna(0)
    stock_returns = market_returns * 1.5 + np.random.randn(len(market_returns)) * 0.005
    closes = 50 * np.cumprod(1 + stock_returns)
    
    return pd.DataFrame({
        'open': closes * 0.99,
        'high': closes * 1.02,
        'low': closes * 0.98,
        'close': closes,
        'volume': np.random.randint(1000000, 5000000, len(closes))
    }, index=market_data.index)


@pytest.fixture
def low_beta_stock(market_data):
    """Düşük beta hisse (piyasadan 0.5x volatil)"""
    np.random.seed(456)
    market_returns = market_data['close'].pct_change().fillna(0)
    stock_returns = market_returns * 0.5 + np.random.randn(len(market_returns)) * 0.003
    closes = 75 * np.cumprod(1 + stock_returns)
    
    return pd.DataFrame({
        'open': closes * 0.99,
        'high': closes * 1.01,
        'low': closes * 0.99,
        'close': closes,
        'volume': np.random.randint(500000, 2000000, len(closes))
    }, index=market_data.index)


class TestCalculateBeta:
    """calculate_beta fonksiyonu testleri"""
    
    def test_returns_dict(self, high_beta_stock, market_data):
        """Dictionary döndürmeli"""
        result = calculate_beta(high_beta_stock, market_data)
        assert isinstance(result, dict)
    
    def test_contains_required_keys(self, high_beta_stock, market_data):
        """Gerekli anahtarları içermeli"""
        result = calculate_beta(high_beta_stock, market_data)
        required_keys = ['beta', 'correlation', 'r_squared', 'alpha', 'volatility_ratio']
        for key in required_keys:
            assert key in result
    
    def test_high_beta_greater_than_one(self, high_beta_stock, market_data):
        """Yüksek volatil hisse beta > 1 olmalı"""
        result = calculate_beta(high_beta_stock, market_data)
        assert result['beta'] > 1.0
    
    def test_low_beta_less_than_one(self, low_beta_stock, market_data):
        """Düşük volatil hisse beta < 1 olmalı"""
        result = calculate_beta(low_beta_stock, market_data)
        assert result['beta'] < 1.0
    
    def test_correlation_in_range(self, high_beta_stock, market_data):
        """Korelasyon -1 ile 1 arasında olmalı"""
        result = calculate_beta(high_beta_stock, market_data)
        assert -1 <= result['correlation'] <= 1
    
    def test_r_squared_in_range(self, high_beta_stock, market_data):
        """R-kare 0 ile 1 arasında olmalı"""
        result = calculate_beta(high_beta_stock, market_data)
        assert 0 <= result['r_squared'] <= 1
    
    def test_none_stock(self, market_data):
        """None stock için varsayılan döndürmeli"""
        result = calculate_beta(None, market_data)
        assert result['beta'] == 1.0
        assert result['data_points'] == 0
    
    def test_none_benchmark(self, high_beta_stock):
        """None benchmark için varsayılan döndürmeli"""
        result = calculate_beta(high_beta_stock, None)
        assert result['beta'] == 1.0
    
    def test_insufficient_data(self, market_data):
        """Yetersiz veri için varsayılan döndürmeli"""
        short_stock = market_data.head(10)
        result = calculate_beta(short_stock, market_data)
        assert result['data_points'] == 0


class TestRollingBeta:
    """Rolling beta testleri"""
    
    def test_returns_series(self, high_beta_stock, market_data):
        """Series döndürmeli"""
        result = calculate_rolling_beta(high_beta_stock, market_data, window=60)
        assert isinstance(result, pd.Series)
    
    def test_length_matches_window(self, high_beta_stock, market_data):
        """Sonuç uzunluğu window'a göre olmalı"""
        result = calculate_rolling_beta(high_beta_stock, market_data, window=60)
        # En az window kadar veri kaybı olmalı
        assert len(result) <= len(market_data) - 59
    
    def test_none_input(self, market_data):
        """None input için boş Series"""
        result = calculate_rolling_beta(None, market_data)
        assert len(result) == 0


class TestBetaClassification:
    """Beta sınıflandırma testleri"""
    
    def test_negative_beta(self):
        """Negatif beta sınıflandırması"""
        category, desc = get_beta_classification(-0.5)
        assert category == "Negatif"
    
    def test_very_low_beta(self):
        """Çok düşük beta (< 0.5)"""
        category, _ = get_beta_classification(0.3)
        assert category == "Çok Düşük"
    
    def test_low_beta(self):
        """Düşük beta (0.5 - 0.8)"""
        category, _ = get_beta_classification(0.6)
        assert category == "Düşük"
    
    def test_neutral_low_beta(self):
        """Nötr-düşük beta (0.8 - 1.0)"""
        category, _ = get_beta_classification(0.9)
        assert category == "Nötr-Düşük"
    
    def test_neutral_high_beta(self):
        """Nötr-yüksek beta (1.0 - 1.2)"""
        category, _ = get_beta_classification(1.1)
        assert category == "Nötr-Yüksek"
    
    def test_high_beta(self):
        """Yüksek beta (1.2 - 1.5)"""
        category, _ = get_beta_classification(1.3)
        assert category == "Yüksek"
    
    def test_very_high_beta(self):
        """Çok yüksek beta (> 1.5)"""
        category, _ = get_beta_classification(2.0)
        assert category == "Çok Yüksek"


class TestBetaAdjustedPosition:
    """Beta ayarlı pozisyon testleri"""
    
    def test_high_beta_reduces_position(self):
        """Yüksek beta pozisyonu küçültmeli"""
        base = 100
        adjusted = get_beta_adjusted_position(base, 2.0, 1.0)
        assert adjusted < base
    
    def test_low_beta_increases_position(self):
        """Düşük beta pozisyonu büyütmeli"""
        base = 100
        adjusted = get_beta_adjusted_position(base, 0.5, 1.0)
        assert adjusted > base
    
    def test_neutral_beta_no_change(self):
        """Nötr beta pozisyonu değiştirmemeli"""
        base = 100
        adjusted = get_beta_adjusted_position(base, 1.0, 1.0)
        assert adjusted == base
    
    def test_minimum_one_share(self):
        """En az 1 adet döndürmeli"""
        adjusted = get_beta_adjusted_position(1, 10.0, 1.0)
        assert adjusted >= 1
    
    def test_zero_beta_no_change(self):
        """Sıfır/negatif beta için değişiklik yok"""
        base = 100
        adjusted = get_beta_adjusted_position(base, 0, 1.0)
        assert adjusted == base


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
