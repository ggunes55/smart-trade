# tests/unit/test_basic_filters.py
"""
Basic Filters Unit Tests - Exchange-Specific Filtering
"""
import pytest
import pandas as pd
import numpy as np
import sys
import os

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

from filters.basic_filters import (
    EXCHANGE_FILTER_CONFIGS,
    get_exchange_filter_config,
    get_effective_filter_values,
    pre_filter_junk_stocks,
    basic_filters,
    has_higher_lows
)


class TestExchangeConfigs:
    """Exchange konfigürasyon testleri"""
    
    def test_bist_config_exists(self):
        """BIST config mevcut olmalı"""
        assert 'BIST' in EXCHANGE_FILTER_CONFIGS
        config = EXCHANGE_FILTER_CONFIGS['BIST']
        assert config['min_rsi'] == 25
        assert config['max_rsi'] == 75
        assert config['min_volume_20d_avg'] == 100000
        assert config['min_avg_price'] == 1.0
    
    def test_nasdaq_config_exists(self):
        """NASDAQ config mevcut olmalı"""
        assert 'NASDAQ' in EXCHANGE_FILTER_CONFIGS
        config = EXCHANGE_FILTER_CONFIGS['NASDAQ']
        assert config['min_rsi'] == 30
        assert config['max_rsi'] == 70
        assert config['min_volume_20d_avg'] == 500000
        assert config['min_avg_price'] == 5.0
    
    def test_nyse_config_exists(self):
        """NYSE config mevcut olmalı"""
        assert 'NYSE' in EXCHANGE_FILTER_CONFIGS
        config = EXCHANGE_FILTER_CONFIGS['NYSE']
        assert config['min_rsi'] == 32
        assert config['max_rsi'] == 68
        assert config['min_volume_20d_avg'] == 300000
    
    def test_get_exchange_filter_config_bist(self):
        """BIST config'i doğru dönmeli"""
        config = get_exchange_filter_config('BIST')
        assert config['name'] == 'Borsa Istanbul'
    
    def test_get_exchange_filter_config_unknown(self):
        """Bilinmeyen exchange için BIST döndürmeli"""
        config = get_exchange_filter_config('UNKNOWN')
        assert config['name'] == 'Borsa Istanbul'


class TestEffectiveFilterValues:
    """Efektif filtre değerleri testleri"""
    
    def test_auto_mode_uses_exchange_config(self):
        """Auto mod exchange config kullanmalı"""
        user_config = {'min_rsi': 40, 'max_rsi': 60}
        effective = get_effective_filter_values(user_config, 'BIST', auto_mode=True)
        
        # Exchange config değerlerini kullanmalı, user config değil
        assert effective['min_rsi'] == 25  # BIST değeri
        assert effective['max_rsi'] == 75  # BIST değeri
    
    def test_manual_mode_uses_user_config(self):
        """Manuel mod user config kullanmalı"""
        user_config = {'min_rsi': 40, 'max_rsi': 60}
        effective = get_effective_filter_values(user_config, 'BIST', auto_mode=False)
        
        # User config değerlerini kullanmalı
        assert effective['min_rsi'] == 40
        assert effective['max_rsi'] == 60


class TestPreFilterJunkStocks:
    """Çöp hisse ön filtre testleri"""
    
    @pytest.fixture
    def good_stock_df(self):
        """İyi bir hisse için örnek veri"""
        dates = pd.date_range('2024-01-01', periods=100, freq='D')
        return pd.DataFrame({
            'open': np.random.uniform(10, 12, 100),
            'high': np.random.uniform(11, 13, 100),
            'low': np.random.uniform(9, 11, 100),
            'close': np.random.uniform(10, 12, 100),
            'volume': np.random.randint(200000, 500000, 100)
        }, index=dates)
    
    @pytest.fixture
    def low_volume_df(self):
        """Düşük hacimli hisse"""
        dates = pd.date_range('2024-01-01', periods=100, freq='D')
        return pd.DataFrame({
            'open': np.random.uniform(10, 12, 100),
            'high': np.random.uniform(11, 13, 100),
            'low': np.random.uniform(9, 11, 100),
            'close': np.random.uniform(10, 12, 100),
            'volume': np.random.randint(1000, 5000, 100)  # Çok düşük hacim
        }, index=dates)
    
    @pytest.fixture
    def penny_stock_df(self):
        """Penny stock (düşük fiyat)"""
        dates = pd.date_range('2024-01-01', periods=100, freq='D')
        return pd.DataFrame({
            'open': np.random.uniform(0.1, 0.5, 100),
            'high': np.random.uniform(0.2, 0.6, 100),
            'low': np.random.uniform(0.05, 0.4, 100),
            'close': np.random.uniform(0.1, 0.5, 100),  # 1 TL altı
            'volume': np.random.randint(200000, 500000, 100)
        }, index=dates)
    
    def test_good_stock_passes(self, good_stock_df):
        """İyi hisse ön filtreyi geçmeli"""
        passed, reason = pre_filter_junk_stocks(good_stock_df, 'BIST')
        assert passed is True
        assert reason == "Ön filtre geçti"
    
    def test_low_volume_fails(self, low_volume_df):
        """Düşük hacimli hisse elenmeli"""
        passed, reason = pre_filter_junk_stocks(low_volume_df, 'BIST')
        assert passed is False
        assert "Düşük hacim" in reason
    
    def test_penny_stock_fails(self, penny_stock_df):
        """Penny stock elenmeli"""
        passed, reason = pre_filter_junk_stocks(penny_stock_df, 'BIST')
        assert passed is False
        assert "Düşük fiyat" in reason
    
    def test_insufficient_data(self):
        """Yetersiz veri elenmeli"""
        df = pd.DataFrame({'close': [1, 2, 3], 'volume': [100, 200, 300]})
        passed, reason = pre_filter_junk_stocks(df, 'BIST')
        assert passed is False
        assert "Yetersiz veri" in reason


class TestBasicFilters:
    """Basic filters ana fonksiyon testleri"""
    
    @pytest.fixture
    def good_latest(self):
        """Filtreleri geçecek örnek veri"""
        return {
            'symbol': 'TEST',
            'close': 10.0,
            'volume': 300000,
            'RSI': 50,
            'Relative_Volume': 1.5,
            'EMA20': 9.5,
            'EMA50': 9.0,
            'MACD_Level': 0.5,
            'MACD_Signal': 0.3,
            'ADX': 25,
            'CMF': 0.1,
            'Daily_Change_Pct': 2.0,
            'Volume_20d_Avg': 200000,
        }
    
    @pytest.fixture
    def test_config(self):
        """Test config"""
        return {
            'debug_mode': False,
            'exchange': 'BIST',
            'filter_mode': 'auto'
        }
    
    def test_good_stock_passes_auto_mode(self, good_latest, test_config):
        """İyi hisse auto modda geçmeli"""
        result = basic_filters(good_latest, test_config, None, 'BIST', auto_mode=True)
        assert result is True
    
    def test_high_rsi_fails(self, good_latest, test_config):
        """Yüksek RSI elenmeli"""
        good_latest['RSI'] = 85  # Max 75 for BIST
        result = basic_filters(good_latest, test_config, None, 'BIST', auto_mode=True)
        assert result is False
    
    def test_low_rsi_fails(self, good_latest, test_config):
        """Düşük RSI elenmeli"""
        good_latest['RSI'] = 20  # Min 25 for BIST
        result = basic_filters(good_latest, test_config, None, 'BIST', auto_mode=True)
        assert result is False
    
    def test_low_relative_volume_fails(self, good_latest, test_config):
        """Düşük relative volume elenmeli"""
        good_latest['Relative_Volume'] = 0.3  # Min 0.8 for BIST
        result = basic_filters(good_latest, test_config, None, 'BIST', auto_mode=True)
        assert result is False


class TestHasHigherLows:
    """Yükselen dip kontrol testleri"""
    
    def test_rising_lows(self):
        """Yükselen dipler tespit edilmeli"""
        df = pd.DataFrame({
            'low': list(range(1, 21))  # Sürekli yükselen
        })
        assert has_higher_lows(df, min_count=5) is True
    
    def test_falling_lows(self):
        """Düşen dipler tespit edilmemeli"""
        df = pd.DataFrame({
            'low': list(range(20, 0, -1))  # Sürekli düşen
        })
        assert has_higher_lows(df, min_count=5) is False
    
    def test_insufficient_data(self):
        """Yetersiz veri False dönmeli"""
        df = pd.DataFrame({'low': [1, 2, 3]})
        assert has_higher_lows(df, min_count=2) is False


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
