# -*- coding: utf-8 -*-
"""Integration tests for Scanner"""
import pytest
from unittest.mock import patch

@pytest.mark.integration
class TestScannerIntegration:
    """Scanner entegrasyon testleri"""
    
    def test_market_analysis(self, test_config, sample_ohlcv_data):
        """Test piyasa analizi"""
        from scanner import SwingHunterUltimate
        
        with patch('scanner.data_handler.TvDatafeed') as mock_tv:
            mock_tv.return_value.get_hist.return_value = sample_ohlcv_data
            hunter = SwingHunterUltimate()
            
            with patch.object(hunter.data_handler, 'safe_api_call', return_value=sample_ohlcv_data):
                market = hunter.analyze_market_condition()
                assert market is not None
                assert market.regime in ['bullish', 'bearish', 'volatile', 'sideways', 'neutral']
    
    def test_excel_export(self, test_config, cleanup_test_files):
        """Test Excel export"""
        from scanner import SwingHunterUltimate
        
        hunter = SwingHunterUltimate()
        test_results = {
            'Swing Uygun': [
                {'Hisse': 'GARAN', 'Skor': '85/100', 'Fiyat': '100.50'}
            ]
        }
        filename = hunter.save_to_excel(test_results)
        assert filename is not None
        assert filename.endswith('.xlsx')
