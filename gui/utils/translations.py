# -*- coding: utf-8 -*-
"""
Turkish Translations Module - Türkçe Çeviri Modülü
Tüm İngilizce terimlerin Türkçe karşılıkları
"""

# Term translations (English -> Turkish)
TRANSLATIONS = {
    # Trend terms
    'strong': 'güçlü',
    'weak': 'zayıf',
    'medium': 'orta',
    'bullish': 'yükseliş',
    'bearish': 'düşüş',
    'up': 'yukarı',
    'down': 'aşağı',
    'sideways': 'yatay',
    'neutral': 'nötr',
    
    # Signal terms
    'buy': 'al',
    'sell': 'sat',
    'hold': 'bekle',
    'early': 'erken',
    'late': 'geç',
    'signal': 'sinyal',
    
    # Indicator status
    'overbought': 'aşırı alım',
    'oversold': 'aşırı satım',
    'positive': 'pozitif',
    'negative': 'negatif',
    'extreme': 'aşırı',
    
    # Analysis terms
    'volume': 'hacim',
    'above': 'üstü',
    'below': 'altı',
    'average': 'ortalama',
    'support': 'destek',
    'resistance': 'direnç',
    'nearby': 'yakın',
    'aligned': 'hizalı',
    'momentum': 'momentum',
    'trend': 'trend',
    'volatility': 'volatilite',
    'acceptable': 'kabul edilebilir',
    'crossover': 'kesişim',
    'divergence': 'uyumsuzluk',
    
    # Entry checklist items (full phrases)
    'volume_above_average': 'Hacim Ortalamanın Üstünde',
    'rsi_not_extreme': 'RSI Aşırı Değil',
    'trend_aligned': 'Trend Hizalı',
    'support_nearby': 'Destek Yakın',
    'momentum_positive': 'Momentum Pozitif',
    'volatility_acceptable': 'Volatilite Kabul Edilebilir',
    
    # Quality levels
    'high_quality': 'Yüksek Kalite',
    'medium_quality': 'Orta Kalite',
    'low_quality': 'Düşük Kalite',
    'high': 'yüksek',
    'low': 'düşük',
    
    # Status terms
    'active': 'aktif',
    'passive': 'pasif',
    'ready': 'hazır',
    'wait': 'bekle',
    'pending': 'beklemede',
    'completed': 'tamamlandı',
    'failed': 'başarısız',
    'success': 'başarılı',
    
    # Market terms
    'consolidation': 'konsolidasyon',
    'breakout': 'kırılım',
    'breakdown': 'düşüş kırılımı',
    'pullback': 'geri çekilme',
    'retracement': 'düzeltme',
    'reversal': 'dönüş',
    'continuation': 'devam',
    
    # Common technical terms
    'entry': 'giriş',
    'exit': 'çıkış',
    'stop': 'zarar kes',
    'target': 'hedef',
    'risk': 'risk',
    'reward': 'kazanç',
    'ratio': 'oranı',
    'score': 'skor',
    'quality': 'kalite',
    'strength': 'güç',
}


def translate(text: str) -> str:
    """
    Translate English text to Turkish.
    Handles both single words and phrases.
    
    Args:
        text: Text to translate
        
    Returns:
        Translated text (Turkish)
    """
    if not text or not isinstance(text, str):
        return text
    
    # First check for exact match (for full phrases like 'volume_above_average')
    lower_text = text.lower().strip()
    if lower_text in TRANSLATIONS:
        translated = TRANSLATIONS[lower_text]
        # Preserve original case
        if text[0].isupper():
            return translated.title()
        return translated
    
    # Try word-by-word translation
    result = text
    for eng, tr in sorted(TRANSLATIONS.items(), key=lambda x: len(x[0]), reverse=True):
        # Case-insensitive replacement
        import re
        pattern = re.compile(re.escape(eng), re.IGNORECASE)
        result = pattern.sub(tr, result)
    
    return result


def translate_dict_keys(d: dict) -> dict:
    """
    Translate dictionary keys from English to Turkish.
    
    Args:
        d: Dictionary with English keys
        
    Returns:
        Dictionary with translated keys
    """
    if not d:
        return d
    
    return {translate(k): v for k, v in d.items()}


def translate_checklist(checklist: dict) -> dict:
    """
    Translate entry checklist items.
    
    Args:
        checklist: Dictionary of checklist items {english_key: bool}
        
    Returns:
        Dictionary with Turkish keys
    """
    if not checklist:
        return checklist
    
    translated = {}
    for key, value in checklist.items():
        tr_key = translate(key.replace('_', ' '))
        translated[tr_key] = value
    
    return translated


def format_trend_turkish(trend: str) -> str:
    """Format trend value in Turkish"""
    if not trend:
        return '-'
    
    trend_upper = str(trend).upper()
    if 'UP' in trend_upper or 'YÜK' in trend_upper:
        return '↑ Yükseliş'
    elif 'DOWN' in trend_upper or 'DÜŞ' in trend_upper:
        return '↓ Düşüş'
    elif 'SIDE' in trend_upper or 'YAT' in trend_upper:
        return '→ Yatay'
    return translate(trend)


def format_strength_turkish(strength: str) -> str:
    """Format strength value in Turkish"""
    if not strength:
        return '-'
    
    strength_upper = str(strength).upper()
    if 'STRONG' in strength_upper or 'GÜÇ' in strength_upper:
        return 'Güçlü'
    elif 'MEDIUM' in strength_upper or 'ORTA' in strength_upper:
        return 'Orta'
    elif 'WEAK' in strength_upper or 'ZAYIF' in strength_upper:
        return 'Zayıf'
    return translate(strength)
