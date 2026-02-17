# risk/position_sizer.py
"""
Pozisyon Boyutlandırma Modülü

Bu modül, risk yönetimi prensiplerine göre optimal pozisyon boyutunu hesaplar.
Kelly Criterion ve sabit risk yaklaşımlarını destekler.
"""
import numpy as np
from typing import Dict, Optional


def calculate_position_size(
    entry_price: float, 
    stop_loss: float, 
    account_balance: float, 
    risk_pct: float = 1.0
) -> int:
    """
    Risk yüzdesine göre pozisyon boyutunu hesaplar.
    
    Formül: Pozisyon = (Sermaye × Risk%) / (Giriş - Stop)
    
    Args:
        entry_price: Planlanan giriş fiyatı (TL/USD)
        stop_loss: Stop-loss fiyat seviyesi (TL/USD)
        account_balance: Hesap bakiyesi (TL/USD)
        risk_pct: İşlem başına risk yüzdesi (varsayılan: %1)
    
    Returns:
        Alınacak hisse/lot adedi (en az 1)
    
    Raises:
        ValueError: Geçersiz parametre değerleri için
    
    Example:
        >>> calculate_position_size(100, 95, 10000, 2.0)
        40  # (10000 × 0.02) / (100 - 95) = 40 adet
    """
    if stop_loss <= 0 or entry_price <= 0:
        return 0
    if account_balance <= 0:
        return 0
    if risk_pct <= 0 or risk_pct > 100:
        return 0
        
    risk_amount = account_balance * (risk_pct / 100)
    risk_per_share = abs(entry_price - stop_loss)
    
    if risk_per_share <= 0:
        return 0
        
    position_size = risk_amount / risk_per_share
    return max(1, int(position_size))


def validate_risk_parameters(config: Dict, account_balance: float) -> Dict:
    """
    Risk parametrelerini doğrular ve güvenli aralıklara çeker.
    
    Args:
        config: Konfigürasyon dictionary'si
            - max_risk_pct: İşlem başına max risk %
            - min_risk_reward_ratio: Min R/R oranı
            - max_position_size_pct: Max pozisyon % (sermayeye göre)
        account_balance: Mevcut hesap bakiyesi
    
    Returns:
        Doğrulanmış ve sınırlandırılmış parametreler
    
    Example:
        >>> validate_risk_parameters({'max_risk_pct': 10}, 10000)
        {'risk_pct': 5.0, ...}  # 10 çok yüksek, 5'e düşürüldü
    """
    validated = {
        'risk_pct': config.get('max_risk_pct', 1.0),
        'min_rr_ratio': config.get('min_risk_reward_ratio', 2.0),
        'max_position_size_pct': config.get('max_position_size_pct', 10.0),
        'account_balance': account_balance
    }
    
    # Güvenli aralıklara çek
    validated['risk_pct'] = max(0.1, min(5.0, validated['risk_pct']))
    validated['min_rr_ratio'] = max(1.0, validated['min_rr_ratio'])
    validated['max_position_size_pct'] = min(100.0, max(1.0, validated['max_position_size_pct']))
    
    return validated


def calculate_kelly_position(
    win_rate: float, 
    avg_win: float, 
    avg_loss: float
) -> float:
    """
    Kelly Criterion ile optimal pozisyon boyutu hesaplar.
    
    Formül: f* = (bp - q) / b
    Burada:
        f* = Optimal pozisyon oranı
        b = Ortalama kazanç / ortalama kayıp
        p = Kazanma olasılığı
        q = Kaybetme olasılığı (1 - p)
    
    Args:
        win_rate: Kazanan işlem yüzdesi (0-100)
        avg_win: Ortalama kazanç miktarı
        avg_loss: Ortalama kayıp miktarı (pozitif değer)
    
    Returns:
        Optimal sermaye kullanım oranı (0.0 - 1.0)
        Negatif veya çok yüksek değerler 0 veya 0.25 ile sınırlandırılır
    
    Note:
        Kelly genellikle çok agresif olduğundan, half-Kelly (sonuç/2)
        veya quarter-Kelly kullanımı önerilir.
    """
    if avg_loss <= 0 or avg_win <= 0:
        return 0.0
    
    p = win_rate / 100  # Kazanma olasılığı
    q = 1 - p  # Kaybetme olasılığı
    b = avg_win / avg_loss  # Odds ratio
    
    # Kelly formülü
    kelly = (b * p - q) / b
    
    # Güvenlik sınırları
    if kelly < 0:
        return 0.0
    
    # Max %25 sermaye kullanımı (quarter Kelly mantığı)
    return min(kelly, 0.25)