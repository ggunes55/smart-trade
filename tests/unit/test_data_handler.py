# -*- coding: utf-8 -*-
"""Unit tests for DataHandler"""
import pytest
from unittest.mock import MagicMock
from tvDatafeed import Interval

@pytest.mark.unit
class TestDataHandler:
    """DataHandler unit tests"""
    
    def test_initialization(self, test_config):
        """Test DataHandler başlatma"""
        from scanner.data_handler import DataHandler
        handler = DataHandler(test_config)
        assert handler.cfg == test_config
        assert handler.tv is not None
    
    def test_safe_api_call_success(self, data_handler, sample_ohlcv_data):
        """Test başarılı API çağrısı"""
        data_handler.tv.get_hist.return_value = sample_ohlcv_data
        result = data_handler.safe_api_call('GARAN', 'BIST', Interval.in_daily, 100)
        assert result is not None
        assert len(result) > 0
    
    def test_get_daily_data(self, data_handler, sample_ohlcv_data):
        """Test günlük veri çekme"""
        data_handler.tv.get_hist.return_value = sample_ohlcv_data
        result = data_handler.get_daily_data('GARAN', 'BIST')
        assert result is not None
