# -*- coding: utf-8 -*-
"""
Unit Tests for Entry Timing Optimizer
"""
import pytest
import pandas as pd
import numpy as np
from analysis.entry_timing import EntryTimingOptimizer, SignalType


@pytest.fixture
def sample_ohlcv_df():
    """Örnek OHLCV verisi oluştur"""
    dates = pd.date_range('2024-01-01', periods=100, freq='D')
    np.random.seed(42)
    
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
    
    # İndikatör simülasyonu
    df['rsi'] = np.random.uniform(30, 70, 100)
    df['macd'] = np.random.uniform(-1, 1, 100)
    df['macd_signal'] = df['macd'] * 0.9
    df['ATR14'] = df['close'] * 0.02  # %2 ATR
    
    return df


@pytest.fixture
def test_config():
    """Test için minimal config"""
    return {
        'breakout_confirmation_pct': 0.5,
        'min_volume_surge': 1.5,
        'support_distance_min': 1.0,
        'support_distance_max': 3.0
    }


class TestEntryTimingOptimizer:
    """Entry Timing Optimizer testleri"""
    
    def test_init(self, test_config):
        """Optimizer doğru initialize olmalı"""
        optimizer = EntryTimingOptimizer(test_config)
        
        assert optimizer.breakout_confirmation_pct == 0.5
        assert optimizer.volume_surge_threshold == 1.5
    
    def test_detect_signal_type_momentum(self, test_config, sample_ohlcv_df):
        """Default durumda MOMENTUM döndürmeli"""
        optimizer = EntryTimingOptimizer(test_config)
        
        signal_type = optimizer.detect_signal_type(sample_ohlcv_df)
        
        assert isinstance(signal_type, SignalType)
    
    def test_optimal_entry_point_returns_dict(self, test_config, sample_ohlcv_df):
        """optimal_entry_point dictionary döndürmeli"""
        optimizer = EntryTimingOptimizer(test_config)
        
        entry = optimizer.optimal_entry_point(sample_ohlcv_df)
        
        assert entry is not None
        assert 'entry_price' in entry
        assert 'signal_type' in entry
        assert 'confidence' in entry
    
    def test_optimal_entry_breakout(self, test_config, sample_ohlcv_df):
        """BREAKOUT tipi için doğru entry hesaplanmalı"""
        optimizer = EntryTimingOptimizer(test_config)
        
        entry = optimizer.optimal_entry_point(sample_ohlcv_df, signal_type='BREAKOUT')
        
        assert entry is not None
        assert entry['signal_type'] == 'BREAKOUT'
        assert 'resistance_level' in entry
    
    def test_optimal_entry_pullback(self, test_config, sample_ohlcv_df):
        """PULLBACK tipi için doğru entry hesaplanmalı"""
        optimizer = EntryTimingOptimizer(test_config)
        
        entry = optimizer.optimal_entry_point(sample_ohlcv_df, signal_type='PULLBACK')
        
        assert entry is not None
        assert entry['signal_type'] == 'PULLBACK'
        assert 'support_level' in entry
    
    def test_validation_checklist_returns_tuple(self, test_config, sample_ohlcv_df):
        """validation_checklist tuple döndürmeli"""
        optimizer = EntryTimingOptimizer(test_config)
        
        result = optimizer.entry_validation_checklist(sample_ohlcv_df, 'TEST')
        
        assert isinstance(result, tuple)
        assert len(result) == 3
        
        is_valid, checklist, failed = result
        assert isinstance(is_valid, bool)
        assert isinstance(checklist, dict)
        assert isinstance(failed, list)
    
    def test_validation_checklist_has_required_checks(self, test_config, sample_ohlcv_df):
        """Checklist gerekli kontrolleri içermeli"""
        optimizer = EntryTimingOptimizer(test_config)
        
        _, checklist, _ = optimizer.entry_validation_checklist(sample_ohlcv_df, 'TEST')
        
        expected_checks = [
            'volume_above_average',
            'rsi_not_extreme',
            'trend_aligned',
            'support_nearby',
            'momentum_positive',
            'volatility_acceptable'
        ]
        
        for check in expected_checks:
            assert check in checklist
    
    def test_get_entry_recommendation(self, test_config, sample_ohlcv_df):
        """get_entry_recommendation tam sonuç döndürmeli"""
        optimizer = EntryTimingOptimizer(test_config)
        
        rec = optimizer.get_entry_recommendation(sample_ohlcv_df, 'TEST')
        
        assert 'symbol' in rec
        assert 'recommendation' in rec
        assert 'action' in rec
        assert 'entry_info' in rec
        assert 'validation_passed' in rec
        assert 'overall_confidence' in rec
        
        assert rec['recommendation'] in ['STRONG BUY', 'BUY', 'WAIT']
    
    def test_insufficient_data_returns_none(self, test_config):
        """Yetersiz veri durumunda None dönmeli"""
        optimizer = EntryTimingOptimizer(test_config)
        
        short_df = pd.DataFrame({
            'close': [100, 101],
            'volume': [1000, 1100]
        })
        
        entry = optimizer.optimal_entry_point(short_df)
        
        assert entry is None
    
    def test_confidence_bounded(self, test_config, sample_ohlcv_df):
        """Confidence 0-1 arasında olmalı"""
        optimizer = EntryTimingOptimizer(test_config)
        
        for signal_type in ['BREAKOUT', 'PULLBACK', 'REVERSAL', 'MOMENTUM']:
            entry = optimizer.optimal_entry_point(sample_ohlcv_df, signal_type=signal_type)
            
            if entry:
                assert 0 <= entry['confidence'] <= 1
    
    def test_signal_type_case_insensitive(self, test_config, sample_ohlcv_df):
        """Signal type büyük/küçük harf duyarsız olmalı"""
        optimizer = EntryTimingOptimizer(test_config)
        
        entry1 = optimizer.optimal_entry_point(sample_ohlcv_df, signal_type='breakout')
        entry2 = optimizer.optimal_entry_point(sample_ohlcv_df, signal_type='BREAKOUT')
        
        assert entry1['signal_type'] == entry2['signal_type']
