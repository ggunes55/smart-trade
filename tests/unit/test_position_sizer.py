# tests/unit/test_position_sizer.py
"""
Position Sizer Unit Tests - Risk Yönetimi Fonksiyonları
"""
import pytest
import sys
import os

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

from risk.position_sizer import (
    calculate_position_size,
    validate_risk_parameters,
    calculate_kelly_position
)


class TestCalculatePositionSize:
    """calculate_position_size fonksiyonu testleri"""
    
    def test_basic_calculation(self):
        """Temel pozisyon hesaplama"""
        # 10000 TL, %2 risk, 100 TL giriş, 95 TL stop
        # Risk = 10000 * 0.02 = 200 TL
        # Hisse başı risk = 100 - 95 = 5 TL
        # Pozisyon = 200 / 5 = 40 adet
        result = calculate_position_size(100, 95, 10000, 2.0)
        assert result == 40
    
    def test_minimum_one_share(self):
        """En az 1 adet döndürmeli"""
        # Çok küçük sermaye
        result = calculate_position_size(100, 99, 100, 1.0)
        assert result >= 1
    
    def test_zero_stop_loss(self):
        """Sıfır stop-loss için 0 döndürmeli"""
        result = calculate_position_size(100, 0, 10000, 2.0)
        assert result == 0
    
    def test_stop_above_entry(self):
        """Stop > Entry için hesaplama yapmalı (short pozisyon)"""
        result = calculate_position_size(100, 105, 10000, 2.0)
        assert result > 0  # Aynı formül çalışmalı
    
    def test_negative_entry(self):
        """Negatif giriş fiyatı için 0 döndürmeli"""
        result = calculate_position_size(-100, 95, 10000, 2.0)
        assert result == 0
    
    def test_negative_balance(self):
        """Negatif bakiye için 0 döndürmeli"""
        result = calculate_position_size(100, 95, -10000, 2.0)
        assert result == 0
    
    def test_zero_risk_percent(self):
        """Sıfır risk yüzdesi için 0 döndürmeli"""
        result = calculate_position_size(100, 95, 10000, 0)
        assert result == 0
    
    def test_over_100_risk(self):
        """100'den büyük risk yüzdesi için 0 döndürmeli"""
        result = calculate_position_size(100, 95, 10000, 101)
        assert result == 0
    
    def test_high_risk_large_position(self):
        """Yüksek risk yüzdesi büyük pozisyon demek"""
        low_risk = calculate_position_size(100, 95, 10000, 1.0)
        high_risk = calculate_position_size(100, 95, 10000, 5.0)
        assert high_risk > low_risk
    
    def test_tight_stop_large_position(self):
        """Dar stop = büyük pozisyon"""
        wide_stop = calculate_position_size(100, 90, 10000, 2.0)  # 10 TL risk
        tight_stop = calculate_position_size(100, 98, 10000, 2.0)  # 2 TL risk
        assert tight_stop > wide_stop


class TestValidateRiskParameters:
    """validate_risk_parameters fonksiyonu testleri"""
    
    def test_returns_dict(self):
        """Dictionary döndürmeli"""
        result = validate_risk_parameters({}, 10000)
        assert isinstance(result, dict)
    
    def test_limits_risk_pct(self):
        """Risk yüzdesini sınırlandırmalı (0.1 - 5.0)"""
        # Çok yüksek risk
        result = validate_risk_parameters({'max_risk_pct': 50.0}, 10000)
        assert result['risk_pct'] <= 5.0
        
        # Çok düşük risk
        result = validate_risk_parameters({'max_risk_pct': 0.01}, 10000)
        assert result['risk_pct'] >= 0.1
    
    def test_minimum_rr_ratio(self):
        """Min R/R oranı en az 1.0 olmalı"""
        result = validate_risk_parameters({'min_risk_reward_ratio': 0.5}, 10000)
        assert result['min_rr_ratio'] >= 1.0
    
    def test_default_values(self):
        """Varsayılan değerler uygulanmalı"""
        result = validate_risk_parameters({}, 10000)
        assert 'risk_pct' in result
        assert 'min_rr_ratio' in result
        assert 'max_position_size_pct' in result
    
    def test_account_balance_preserved(self):
        """Hesap bakiyesi korunmalı"""
        result = validate_risk_parameters({}, 25000)
        assert result['account_balance'] == 25000


class TestCalculateKellyPosition:
    """Kelly Criterion testleri"""
    
    def test_positive_expectancy(self):
        """Pozitif beklenti için pozitif sonuç"""
        # %60 kazanma, 2:1 ödül
        result = calculate_kelly_position(60, 200, 100)
        assert result > 0
    
    def test_negative_expectancy(self):
        """Negatif beklenti için 0"""
        # %30 kazanma, 1:1 ödül
        result = calculate_kelly_position(30, 100, 100)
        assert result == 0
    
    def test_50_50_with_equal_odds(self):
        """50-50 ve eşit kazanç/kayıp için 0"""
        result = calculate_kelly_position(50, 100, 100)
        assert result == 0
    
    def test_max_25_percent(self):
        """Maksimum %25 sermaye kullanımı"""
        # Çok yüksek kazanma oranı
        result = calculate_kelly_position(95, 200, 50)
        assert result <= 0.25
    
    def test_zero_avg_loss(self):
        """Sıfır kayıp için 0 döndürmeli"""
        result = calculate_kelly_position(60, 100, 0)
        assert result == 0
    
    def test_zero_avg_win(self):
        """Sıfır kazanç için 0 döndürmeli"""
        result = calculate_kelly_position(60, 0, 100)
        assert result == 0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
