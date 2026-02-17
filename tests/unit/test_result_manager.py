# -*- coding: utf-8 -*-
"""Unit tests for ResultManager"""
import pytest

@pytest.mark.unit
class TestResultManager:
    """ResultManager unit tests"""
    
    def test_initialization(self, test_config):
        """Test initialization"""
        from scanner.result_manager import ResultManager
        manager = ResultManager(test_config)
        assert manager.cfg == test_config
    
    def test_format_results(self, result_manager):
        """Test sonuç formatlama"""
        raw = [
            {'Hisse': 'GARAN', 'Skor': '85/100'},
            {'Hisse': 'THYAO', 'Skor': '78/100'}
        ]
        formatted = result_manager.format_results(raw)
        assert 'Swing Uygun' in formatted
        assert len(formatted['Swing Uygun']) == 2
    
    def test_get_summary_stats(self, result_manager):
        """Test özet istatistikler"""
        results = {
            'Swing Uygun': [
                {'Hisse': 'GARAN', 'Skor': '85/100', 'R/R': '1:2.5', 'Risk %': '3.5'}
            ]
        }
        stats = result_manager.get_summary_stats(results)
        assert stats['total_stocks'] == 1
        assert stats['avg_score'] > 0
