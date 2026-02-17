# -*- coding: utf-8 -*-
"""Unit tests for TradeCalculator"""
import pytest

@pytest.mark.unit
class TestTradeCalculator:
    """TradeCalculator unit tests"""
    
    def test_initialization(self, test_config):
        """Test initialization"""
        from scanner.trade_calculator import TradeCalculator
        calc = TradeCalculator(test_config)
        assert calc.cfg == test_config
    
    def test_calculate_trade_plan_valid(self, trade_calculator):
        """Test geçerli trade planı"""
        result = trade_calculator.calculate_trade_plan(
            symbol='GARAN',
            entry_price=100,
            stop_loss=95,
            target1=110,
            capital=10000
        )
        assert result is not None
        assert 'shares' in result
        assert 'investment' in result
        assert result['shares'] > 0
    
    def test_validate_trade_parameters_valid(self, trade_calculator):
        """Test geçerli parametre validasyonu"""
        result = trade_calculator.validate_trade_parameters(
            entry_price=100,
            stop_loss=95,
            target1=110
        )
        assert result['is_valid'] is True
        assert result['score'] > 0
