"""
Test Quick Wins: Signal Confirmation, Adaptive RSI, Multi-Level Exit
"""

import pytest
import pandas as pd
import numpy as np
from datetime import datetime, timedelta

# Import yeni feature'lar
from analysis.signal_confirmation import SignalConfirmationFilter
from risk.stop_target_manager import calculate_multi_level_exit
from scanner.symbol_analyzer import SymbolAnalyzer


class TestSignalConfirmationFilter:
    """Signal Confirmation Filter testleri"""

    @pytest.fixture
    def sample_data(self):
        """Test verisi oluştur"""
        dates = pd.date_range(end=datetime.now(), periods=30, freq='D')
        np.random.seed(42)
        
        close = np.cumsum(np.random.randn(30)) + 100
        high = close + np.abs(np.random.randn(30))
        low = close - np.abs(np.random.randn(30))
        volume = np.random.randint(1000000, 5000000, 30)
        
        df = pd.DataFrame({
            'date': dates,
            'open': close * 0.99,
            'high': high,
            'low': low,
            'close': close,
            'volume': volume,
            'rsi': np.random.uniform(35, 65, 30),
            'adx': np.random.uniform(20, 35, 30)
        })
        
        return df

    def test_initialization(self, sample_data):
        """Sınıf oluşturma testi"""
        config = {}
        confirmer = SignalConfirmationFilter(sample_data, config)
        assert confirmer is not None
        assert len(confirmer.df) == 30

    def test_insufficient_data(self):
        """Yetersiz veri hatası"""
        df = pd.DataFrame({'close': [100, 101, 102]})
        config = {}
        
        with pytest.raises(ValueError):
            SignalConfirmationFilter(df, config)

    def test_rsi_moderation_check(self, sample_data):
        """RSI moderation kontrolü"""
        config = {}
        confirmer = SignalConfirmationFilter(sample_data, config)
        
        result = confirmer._check_rsi_moderation()
        assert isinstance(result, bool)
        # RSI 35-65 aralığında ayarlanmış
        assert result is True

    def test_volume_confirmation(self, sample_data):
        """Hacim onayı kontrolü"""
        config = {}
        confirmer = SignalConfirmationFilter(sample_data, config)
        
        result = confirmer._check_volume_confirmation()
        assert isinstance(result, bool)

    def test_trend_alignment(self, sample_data):
        """Trend alignment kontrolü"""
        config = {}
        confirmer = SignalConfirmationFilter(sample_data, config)
        
        result = confirmer._check_trend_alignment()
        assert isinstance(result, bool)

    def test_multi_source_confirmation(self, sample_data):
        """Çoklu kaynak doğrulama"""
        config = {}
        confirmer = SignalConfirmationFilter(sample_data, config)
        
        is_valid, details = confirmer.multi_source_confirmation()
        
        assert isinstance(is_valid, bool)
        assert isinstance(details, dict)
        assert 'confirmation_count' in details
        assert 'confidence' in details
        assert 'recommendation' in details
        assert details['confidence'] >= 0 and details['confidence'] <= 1

    def test_signal_quality_score(self, sample_data):
        """Sinyal kalite skoru"""
        config = {}
        confirmer = SignalConfirmationFilter(sample_data, config)
        
        score = confirmer.signal_quality_score()
        
        assert isinstance(score, float)
        assert 0 <= score <= 100

    def test_should_trade_decision(self, sample_data):
        """Trade kararı"""
        config = {}
        confirmer = SignalConfirmationFilter(sample_data, config)
        
        # Sinyal yoksa trade etme
        result1 = confirmer.should_trade(False)
        assert result1 is False
        
        # Sinyal varsa doğrulama yap
        result2 = confirmer.should_trade(True)
        assert isinstance(result2, bool)


class TestAdaptiveRSI:
    """Adaptive RSI Threshold testleri"""

    @pytest.fixture
    def analyzer(self):
        """Analyzer örneği oluştur"""
        config = {}
        return SymbolAnalyzer(config, None, None, None)

    @pytest.fixture
    def high_volatility_data(self):
        """Yüksek volatiliteli veri"""
        close = np.array([100.0, 105.0, 95.0, 108.0, 90.0, 110.0] * 5)
        df = pd.DataFrame({'close': close})
        return df

    @pytest.fixture
    def low_volatility_data(self):
        """Düşük volatiliteli veri"""
        close = np.array([100.0, 100.5, 100.2, 100.8, 100.1, 100.9] * 5)
        df = pd.DataFrame({'close': close})
        return df

    def test_high_volatility_thresholds(self, analyzer, high_volatility_data):
        """Yüksek volatilite eşikleri (25/75)"""
        oversold, overbought = analyzer.get_adaptive_rsi_thresholds(high_volatility_data)
        
        # Yüksek volatilite: 25/75
        assert oversold <= 30  # 25 beklenen
        assert overbought >= 70  # 75 beklenen

    def test_low_volatility_thresholds(self, analyzer, low_volatility_data):
        """Düşük volatilite eşikleri (35/65)"""
        oversold, overbought = analyzer.get_adaptive_rsi_thresholds(low_volatility_data)
        
        # Düşük volatilite: 35/65
        assert oversold >= 30  # 35 beklenen
        assert overbought <= 70  # 65 beklenen

    def test_normal_volatility_thresholds(self, analyzer):
        """Normal volatilite eşikleri (30/70)"""
        close = np.array([100.0, 100.5, 101.0, 100.8, 101.2, 100.9] * 5)
        df = pd.DataFrame({'close': close})
        
        oversold, overbought = analyzer.get_adaptive_rsi_thresholds(df)
        
        # Normal volatilite: 30/70
        assert oversold == 30
        assert overbought == 70


class TestMultiLevelExit:
    """Çok seviyeli çıkış stratejisi testleri"""

    def test_basic_three_levels(self):
        """Temel 3 seviye çıkış"""
        entry = 100.0
        risk = 10.0  # Stop = 90
        
        levels = calculate_multi_level_exit(entry, risk, num_levels=3)
        
        assert len(levels) == 3
        assert 'level_1' in levels
        assert 'level_2' in levels
        assert 'level_3' in levels

    def test_level_targets(self):
        """Seviye hedefleri kontrolü"""
        entry = 100.0
        risk = 10.0
        
        levels = calculate_multi_level_exit(entry, risk, num_levels=3, scaling_factor=0.5)
        
        # Level 1: Entry + 0.5 * Risk = 105.0
        assert levels['level_1']['target'] == 105.0
        assert levels['level_1']['profit_r'] == 0.5
        
        # Level 2: Entry + 1.0 * Risk = 110.0
        assert levels['level_2']['target'] == 110.0
        assert levels['level_2']['profit_r'] == 1.0
        
        # Level 3: Entry + 1.5 * Risk = 115.0
        assert levels['level_3']['target'] == 115.0
        assert levels['level_3']['profit_r'] == 1.5

    def test_stop_loss_levels(self):
        """Stop-loss seviyeleri"""
        entry = 100.0
        risk = 10.0
        
        levels = calculate_multi_level_exit(entry, risk)
        
        # Level 1: Break-even (Entry = 100)
        assert levels['level_1']['stop_loss'] == entry
        
        # Level 2: Entry + 0.5R = 105
        assert levels['level_2']['stop_loss'] == entry + (0.5 * risk)
        
        # Level 3: Trailing
        assert levels['level_3']['stop_loss'] == 'trailing'

    def test_position_sizing(self):
        """Pozisyon boyutlandırması"""
        entry = 100.0
        risk = 10.0
        
        levels = calculate_multi_level_exit(entry, risk, num_levels=3)
        
        # Her seviye %33.3
        total_exit_pct = sum(level['exit_pct'] for level in levels.values())
        assert abs(total_exit_pct - 100.0) < 0.5  # Yaklaşık 100%

    def test_different_scaling_factors(self):
        """Farklı scaling faktörleri"""
        entry = 100.0
        risk = 10.0
        
        # Scaling factor 0.33
        levels1 = calculate_multi_level_exit(entry, risk, num_levels=3, scaling_factor=0.33)
        assert levels1['level_1']['target'] < levels1['level_2']['target']
        
        # Scaling factor 1.0
        levels2 = calculate_multi_level_exit(entry, risk, num_levels=3, scaling_factor=1.0)
        assert levels2['level_1']['target'] < levels2['level_2']['target']

    def test_invalid_risk_distance(self):
        """Geçersiz risk mesafesi"""
        entry = 100.0
        risk = 0.0
        
        levels = calculate_multi_level_exit(entry, risk)
        
        assert len(levels) == 0

    def test_four_level_exit(self):
        """4 seviye çıkış stratejisi"""
        entry = 100.0
        risk = 10.0
        
        levels = calculate_multi_level_exit(entry, risk, num_levels=4)
        
        assert len(levels) == 4
        # Dört seviye eşit şekilde bölünmüş
        for level in levels.values():
            assert abs(level['exit_pct'] - 25.0) < 0.1


class TestIntegration:
    """Entegrasyon testleri"""

    def test_full_trading_workflow(self):
        """Tam trading workflow testi"""
        # 1. Signal Confirmation
        dates = pd.date_range(end=np.datetime64('now'), periods=30, freq='D')
        close = np.cumsum(np.random.randn(30)) + 100
        df = pd.DataFrame({
            'date': dates,
            'close': close,
            'high': close + 1,
            'low': close - 1,
            'volume': np.random.randint(1000000, 5000000, 30),
            'rsi': np.random.uniform(40, 60, 30),
            'adx': np.random.uniform(25, 35, 30)
        })
        
        confirmer = SignalConfirmationFilter(df, {})
        is_valid, details = confirmer.multi_source_confirmation()
        
        # 2. Adaptive RSI
        analyzer = SymbolAnalyzer({}, None, None, None)
        oversold, overbought = analyzer.get_adaptive_rsi_thresholds(df)
        
        # 3. Multi-Level Exit
        entry = 100.0
        risk = 5.0
        levels = calculate_multi_level_exit(entry, risk)
        
        # Hepsi başarılı
        assert is_valid is not None
        assert oversold > 0
        assert len(levels) == 3


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
