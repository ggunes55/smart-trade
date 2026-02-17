# -*- coding: utf-8 -*-
"""
Unit Tests for Market Regime Adapter
"""
import pytest
import pandas as pd
import numpy as np
from analysis.market_regime_adapter import MarketRegimeAdapter, MarketRegime


@pytest.fixture
def sample_index_df():
    """Örnek endeks verisi oluştur"""
    dates = pd.date_range('2024-01-01', periods=250, freq='D')
    np.random.seed(42)
    
    closes = 100 + np.random.randn(250).cumsum()
    
    df = pd.DataFrame({
        'datetime': dates,
        'open': closes * 0.99,
        'high': closes * 1.02,
        'low': closes * 0.98,
        'close': closes,
        'volume': np.random.randint(1000000, 5000000, 250)
    })
    df.set_index('datetime', inplace=True)
    
    # ADX simülasyonu
    df['adx'] = np.random.uniform(15, 50, 250)
    df['rsi'] = np.random.uniform(30, 70, 250)
    
    return df


@pytest.fixture
def test_config():
    """Test için minimal config"""
    return {
        'regime_adx_strong_threshold': 40,
        'regime_adx_weak_threshold': 25,
        'use_market_regime_adapter': True
    }


class TestMarketRegimeAdapter:
    """Market Regime Adapter testleri"""
    
    def test_init(self, test_config):
        """Adapter doğru initialize olmalı"""
        adapter = MarketRegimeAdapter(test_config)
        
        assert adapter.adx_strong_threshold == 40
        assert adapter.adx_weak_threshold == 25
        assert adapter._current_regime is None
    
    def test_detect_strong_uptrend(self, test_config, sample_index_df):
        """Güçlü yükseliş trendi tespit edilmeli"""
        adapter = MarketRegimeAdapter(test_config)
        
        # ADX yüksek, fiyat SMA200 üzerinde
        sample_index_df['adx'] = 45
        sample_index_df['close'] = sample_index_df['close'] + 20  # SMA200'ün üzerine çıkar
        
        regime = adapter.detect_regime(sample_index_df)
        
        assert regime == MarketRegime.STRONG_UPTREND
    
    def test_detect_consolidation(self, test_config, sample_index_df):
        """Konsolidasyon tespit edilmeli"""
        adapter = MarketRegimeAdapter(test_config)
        
        # ADX düşük
        sample_index_df['adx'] = 15
        
        regime = adapter.detect_regime(sample_index_df)
        
        assert regime == MarketRegime.CONSOLIDATION
    
    def test_detect_strong_downtrend(self, test_config):
        """Güçlü düşüş trendi tespit edilmeli"""
        adapter = MarketRegimeAdapter(test_config)
        
        # Özel veri oluştur: fiyat kesinlikle SMA200 altında olacak şekilde
        dates = pd.date_range('2024-01-01', periods=250, freq='D')
        
        # İlk 200 bar yüksek, son 50 bar düşük = SMA200 yüksek, son fiyat düşük
        closes = np.concatenate([
            np.full(200, 150),  # İlk 200 bar yüksek
            np.full(50, 80)    # Son 50 bar düşük
        ])
        
        df = pd.DataFrame({
            'datetime': dates,
            'close': closes,
            'adx': np.full(250, 45),  # ADX yüksek
        })
        df.set_index('datetime', inplace=True)
        
        regime = adapter.detect_regime(df)
        
        assert regime == MarketRegime.STRONG_DOWNTREND
    
    def test_adaptive_parameters_strong_uptrend(self, test_config):
        """Güçlü yükseliş için doğru parametreler döndürülmeli"""
        adapter = MarketRegimeAdapter(test_config)
        
        params = adapter.get_adaptive_parameters(MarketRegime.STRONG_UPTREND)
        
        assert params['max_open_positions'] == 5
        assert params['min_trend_score'] == 70
        assert 'description' in params
    
    def test_adaptive_parameters_consolidation(self, test_config):
        """Konsolidasyon için doğru parametreler döndürülmeli"""
        adapter = MarketRegimeAdapter(test_config)
        
        params = adapter.get_adaptive_parameters(MarketRegime.CONSOLIDATION)
        
        assert params['max_open_positions'] == 1
        assert params['min_trend_score'] == 55
    
    def test_trading_not_allowed_strong_downtrend(self, test_config):
        """Güçlü düşüşte trading yasak olmalı"""
        adapter = MarketRegimeAdapter(test_config)
        
        assert not adapter.is_trading_allowed(MarketRegime.STRONG_DOWNTREND)
        assert adapter.is_trading_allowed(MarketRegime.CONSOLIDATION)
        assert adapter.is_trading_allowed(MarketRegime.STRONG_UPTREND)
    
    def test_filter_candidates_empty_on_downtrend(self, test_config):
        """Güçlü düşüşte tüm adaylar filtrelenmeli"""
        adapter = MarketRegimeAdapter(test_config)
        
        candidates = [
            {'symbol': 'TEST1', 'rsi': 50, 'trend_score': 70, 'volume_ratio': 1.5},
            {'symbol': 'TEST2', 'rsi': 45, 'trend_score': 65, 'volume_ratio': 1.3}
        ]
        
        filtered = adapter.apply_regime_filters(candidates, MarketRegime.STRONG_DOWNTREND)
        
        assert len(filtered) == 0
    
    def test_filter_candidates_limited_by_max_positions(self, test_config):
        """Adaylar max pozisyon sayısına göre kısıtlanmalı"""
        adapter = MarketRegimeAdapter(test_config)
        
        candidates = [
            {'symbol': f'TEST{i}', 'rsi': 50, 'trend_score': 60, 'volume_ratio': 1.6}
            for i in range(10)
        ]
        
        # Consolidation'da max 1 pozisyon
        filtered = adapter.apply_regime_filters(candidates, MarketRegime.CONSOLIDATION)
        assert len(filtered) <= 1
        
        # Strong uptrend'de max 5 pozisyon
        filtered = adapter.apply_regime_filters(candidates, MarketRegime.STRONG_UPTREND)
        assert len(filtered) <= 5
    
    def test_regime_summary(self, test_config, sample_index_df):
        """Rejim özeti doğru döndürülmeli"""
        adapter = MarketRegimeAdapter(test_config)
        
        sample_index_df['adx'] = 30
        adapter.detect_regime(sample_index_df)
        
        summary = adapter.get_regime_summary()
        
        assert 'current_regime' in summary
        assert 'description' in summary
        assert 'max_positions' in summary
        assert 'recommended_action' in summary
    
    def test_insufficient_data_returns_consolidation(self, test_config):
        """Yetersiz veri durumunda CONSOLIDATION dönmeli"""
        adapter = MarketRegimeAdapter(test_config)
        
        # Kısa veri
        short_df = pd.DataFrame({
            'close': [100, 101, 102],
            'adx': [30, 31, 32]
        })
        
        regime = adapter.detect_regime(short_df)
        
        assert regime == MarketRegime.CONSOLIDATION
