# -*- coding: utf-8 -*-
"""Pytest Configuration & Global Fixtures"""
import sys
import os
import pytest
import pandas as pd
import numpy as np
from unittest.mock import MagicMock, patch

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

import logging
logging.disable(logging.CRITICAL)

def pytest_configure(config):
    """Pytest başlangıç ayarları"""
    config.addinivalue_line("markers", "slow: marks tests as slow")
    config.addinivalue_line("markers", "integration: marks tests as integration tests")
    config.addinivalue_line("markers", "unit: marks tests as unit tests")
    config.addinivalue_line("markers", "gui: marks tests as GUI tests")

@pytest.fixture
def test_config():
    """Test için minimal config"""
    return {
        'exchange': 'BIST',
        'lookback_bars': 100,
        'min_rsi': 30,
        'max_rsi': 70,
        'min_relative_volume': 1.0,
        'max_daily_change_pct': 8.0,
        'min_trend_score': 50,
        'min_risk_reward_ratio': 2.0,
        'max_risk_pct': 5.0,
        'initial_capital': 10000,
        'use_smart_filter': True,
        'use_fibonacci': True,
        'use_consolidation': True,
        'use_multi_timeframe': True,
        'cache_dir': 'test_cache',
        'cache_ttl_hours': 1,
        'max_workers': 2
    }

@pytest.fixture
def sample_ohlcv_data():
    """Örnek OHLCV verisi"""
    dates = pd.date_range('2024-01-01', periods=100, freq='D')
    base_price = 100
    trend = np.linspace(0, 20, 100)
    noise = np.random.normal(0, 2, 100)
    closes = base_price + trend + noise
    
    df = pd.DataFrame({
        'datetime': dates,
        'open': closes * 0.99,
        'high': closes * 1.02,
        'low': closes * 0.98,
        'close': closes,
        'volume': np.random.randint(1000000, 5000000, 100)
    })
    df.set_index('datetime', inplace=True)
    return df

@pytest.fixture
def sample_ohlcv_with_indicators(sample_ohlcv_data):
    """İndikatörlü örnek veri"""
    from indicators.ta_manager import calculate_indicators
    return calculate_indicators(sample_ohlcv_data)

@pytest.fixture
def mock_tv_datafeed():
    """Mock TvDatafeed"""
    mock_tv = MagicMock()
    
    def get_hist_side_effect(symbol, exchange, interval, n_bars):
        dates = pd.date_range('2024-01-01', periods=n_bars, freq='D')
        closes = 100 + np.random.randn(n_bars).cumsum()
        df = pd.DataFrame({
            'datetime': dates,
            'open': closes * 0.99,
            'high': closes * 1.02,
            'low': closes * 0.98,
            'close': closes,
            'volume': np.random.randint(1000000, 5000000, n_bars)
        })
        df.set_index('datetime', inplace=True)
        return df
    
    mock_tv.get_hist.side_effect = get_hist_side_effect
    return mock_tv

@pytest.fixture
def data_handler(test_config, mock_tv_datafeed):
    """DataHandler fixture"""
    from scanner.data_handler import DataHandler
    handler = DataHandler(test_config)
    handler.tv = mock_tv_datafeed
    return handler

@pytest.fixture
def trade_calculator(test_config):
    """TradeCalculator fixture"""
    from scanner.trade_calculator import TradeCalculator
    return TradeCalculator(test_config)

@pytest.fixture
def result_manager(test_config):
    """ResultManager fixture"""
    from scanner.result_manager import ResultManager
    return ResultManager(test_config)

@pytest.fixture
def cleanup_test_files():
    """Test dosyalarını temizle"""
    yield
    import glob
    for pattern in ['test_*.xlsx', 'test_*.csv', 'Swing_Test_*.xlsx']:
        for file in glob.glob(pattern):
            try:
                os.remove(file)
            except:
                pass
